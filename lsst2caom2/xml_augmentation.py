# ***********************************************************************
# ******************  CANADIAN ASTRONOMY DATA CENTRE  *******************
# *************  CENTRE CANADIEN DE DONNÉES ASTRONOMIQUES  **************
#
#  (c) 2026.                            (c) 2026.
#  Government of Canada                 Gouvernement du Canada
#  National Research Council            Conseil national de recherches
#  Ottawa, Canada, K1A 0R6              Ottawa, Canada, K1A 0R6
#  All rights reserved                  Tous droits réservés
#
#  NRC disclaims any warranties,        Le CNRC dénie toute garantie
#  expressed, implied, or               énoncée, implicite ou légale,
#  statutory, of any kind with          de quelque nature que ce
#  respect to the software,             soit, concernant le logiciel,
#  including without limitation         y compris sans restriction
#  any warranty of merchantability      toute garantie de valeur
#  or fitness for a particular          marchande ou de pertinence
#  purpose. NRC shall not be            pour un usage particulier.
#  liable in any event for any          Le CNRC ne pourra en aucun cas
#  damages, whether direct or           être tenu responsable de tout
#  indirect, special or general,        dommage, direct ou indirect,
#  consequential or incidental,         particulier ou général,
#  arising from the use of the          accessoire ou fortuit, résultant
#  software.  Neither the name          de l'utilisation du logiciel. Ni
#  of the National Research             le nom du Conseil National de
#  Council of Canada nor the            Recherches du Canada ni les noms
#  names of its contributors may        de ses  participants ne peuvent
#  be used to endorse or promote        être utilisés pour approuver ou
#  products derived from this           promouvoir les produits dérivés
#  software without specific prior      de ce logiciel sans autorisation
#  written permission.                  préalable et particulière
#                                       par écrit.
#
#  This file is part of the             Ce fichier fait partie du projet
#  OpenCADC project.                    OpenCADC.
#
#  OpenCADC is free software:           OpenCADC est un logiciel libre ;
#  you can redistribute it and/or       vous pouvez le redistribuer ou le
#  modify it under the terms of         modifier suivant les termes de
#  the GNU Affero General Public        la “GNU Affero General Public
#  License as published by the          License” telle que publiée
#  Free Software Foundation,            par la Free Software Foundation
#  either version 3 of the              : soit la version 3 de cette
#  License, or (at your option)         licence, soit (à votre gré)
#  any later version.                   toute version ultérieure.
#
#  OpenCADC is distributed in the       OpenCADC est distribué
#  hope that it will be useful,         dans l’espoir qu’il vous
#  but WITHOUT ANY WARRANTY;            sera utile, mais SANS AUCUNE
#  without even the implied             GARANTIE : sans même la garantie
#  warranty of MERCHANTABILITY          implicite de COMMERCIALISABILITÉ
#  or FITNESS FOR A PARTICULAR          ni d’ADÉQUATION À UN OBJECTIF
#  PURPOSE.  See the GNU Affero         PARTICULIER. Consultez la Licence
#  General Public License for           Générale Publique GNU Affero
#  more details.                        pour plus de détails.
#
#  You should have received             Vous devriez avoir reçu une
#  a copy of the GNU Affero             copie de la Licence Générale
#  General Public License along         Publique GNU Affero avec
#  with OpenCADC.  If not, see          OpenCADC ; si ce n’est
#  <http://www.gnu.org/licenses/>.      pas le cas, consultez :
#                                       <http://www.gnu.org/licenses/>.
#
#  $Revision: 4 $
#
# ***********************************************************************
#


"""LSST meta visitor: change Observation XML content before caom2repo store.

Walks Observation -> Plane -> Artifact. Plane-level changes fill missing
data_release / meta_release. Artifact-level changes rewrite the URI via
Butler.getURI and fill missing content_length / checksum.
"""

import datetime
import logging
import urllib.parse

from caom2 import ChecksumURI
from caom2pipe.manage_composable import CadcException, make_datetime


__all__ = [
    'ARTIFACT_URI_FIELD',
    'PLANE_DATA_RELEASE_FIELD',
    'PLANE_META_RELEASE_FIELD',
    'XmlAugmentationVisitor',
    'rekey_artifact',
    'visit',
]

ARTIFACT_URI_FIELD = 'artifact_uri'
PLANE_DATA_RELEASE_FIELD = 'plane_data_release'
PLANE_META_RELEASE_FIELD = 'plane_meta_release'

# Defaults aligned with butler2caom.py for DP1 coadds.
_DEFAULT_SI_PATH_ROOT = '/raven/files/'
# _DEFAULT_OBSERVATION_ID_KEYS = ['skymap', 'tract', 'patch']
_DEFAULT_OBSERVATION_ID_KEYS = ['skymap', 'tract']
_DEFAULT_DATASET_TYPE = 'deep_coadd'
_DEFAULT_INSTRUMENT = 'LSSTComCam'

_LOGGER = logging.getLogger(__name__)


def rekey_artifact(plane, old_uri, new_uri):
    """Move an Artifact to a new URI key in plane.artifacts."""
    if old_uri not in plane.artifacts:
        raise CadcException(f'Artifact {old_uri} not found on plane {plane.product_id}.')
    if old_uri == new_uri:
        return plane.artifacts[old_uri]
    if new_uri in plane.artifacts:
        raise CadcException(
            f'Cannot rewrite {old_uri} to {new_uri}: target URI already exists on plane {plane.product_id}.'
        )
    artifact = plane.artifacts.pop(old_uri)
    artifact.uri = new_uri
    plane.artifacts[new_uri] = artifact
    _LOGGER.debug(f'Rekeyed Artifact {old_uri} -> {new_uri}')
    return artifact


def _to_naive_datetime(value):
    """CAOM2 Plane release fields require a timezone-naive datetime."""
    if value is None:
        return None
    if isinstance(value, datetime.datetime):
        return make_datetime(value)
    if isinstance(value, datetime.date):
        return datetime.datetime(value.year, value.month, value.day)
    return make_datetime(value)


class XmlAugmentationVisitor:
    """Change Observation XML content using config.lookup and an LSST Butler."""

    def __init__(self, observation, **kwargs):
        self.observation = observation
        self.config = kwargs.get('config')
        self.clients = kwargs.get('clients')
        self.storage_name = kwargs.get('storage_name')
        self._logger = logging.getLogger(self.__class__.__name__)
        self._lookup = getattr(self.config, 'lookup', None) or {}

    @property
    def si_path_root(self):
        return self._lookup.get('si_path_root', _DEFAULT_SI_PATH_ROOT)

    @property
    def observation_id_keys(self):
        return list(self._lookup.get('observation_id_keys', _DEFAULT_OBSERVATION_ID_KEYS))

    @property
    def dataset_type(self):
        return self._lookup.get('dataset_type', _DEFAULT_DATASET_TYPE)

    @property
    def instrument(self):
        return self._lookup.get('instrument', _DEFAULT_INSTRUMENT)

    @property
    def configured_data_release(self):
        return _to_naive_datetime(self._lookup.get('data_release'))

    def visit(self):
        if self.observation is None:
            raise CadcException('No Observation for XML augmentation.')
        self._logger.debug(f'Begin XML augmentation for {self.observation.observation_id}')
        for plane in self.observation.planes.values():
            # self._logger.error(f'{plane.product_id}')
            for old_uri in list(plane.artifacts.keys()):
                # self._logger.error(old_uri)
                # TODO need a check to not redo a lookup if it's already been set
                self._rewrite_artifact(self.observation.observation_id, plane, plane.artifacts[old_uri], old_uri)
        self._check_artifact_accessibility()
        self._logger.debug(f'End XML augmentation for {self.observation.observation_id}')
        return self.observation

    def _check_artifact_accessibility(self):
        data_client = getattr(self.clients, 'data_client', None) if self.clients is not None else None
        if data_client is None:
            self._logger.warning('No data client configured; skipping Artifact accessibility checks.')
            return
        for plane in self.observation.planes.values():
            for uri, _artifact in plane.artifacts.items():
                self._logger.debug(f'Checking accessibility for {uri}')
                try:
                    info = data_client.info(uri)
                except Exception as e:
                    raise CadcException(f'Artifact {uri} is not accessible in storage: {e}') from e
                if info is None:
                    raise CadcException(f'Artifact {uri} is not accessible in storage.')

    def _rewrite_plane(self, plane, fields):
        if plane.data_release is None:
            data_release = self.configured_data_release
            if data_release is None:
                raise CadcException(
                    "plane_data_release is listed in uri_rewrite_fields but lookup['data_release'] is missing."
                )
            plane.data_release = data_release
        if plane.meta_release is None:
            plane.meta_release = _to_naive_datetime(
                self.observation.meta_release or datetime.datetime.now()
            )

    def _base_data_id(self):
        keys = self.observation_id_keys
        parts = self.observation.observation_id.split('-')
        if len(parts) < len(keys):
            raise CadcException(
                f'Cannot parse observationID {self.observation.observation_id} into keys {keys}.'
            )
        if len(parts) == len(keys):
            return {k: _coerce(parts[i]) for i, k in enumerate(keys)}
        head = len(parts) - len(keys) + 1
        values = ['-'.join(parts[:head])] + parts[head:]
        return {k: _coerce(values[i]) for i, k in enumerate(keys)}

    def _rewrite_artifact(self, observation_id, plane, artifact, old_uri):
        new_uri, length, md5 = self._lookup_uri_and_meta(observation_id, plane, old_uri)
        rekey_artifact(plane, old_uri, new_uri)
        if artifact.content_length is None and length is not None:
            artifact.content_length = length
        if artifact.content_checksum is None and md5:
            artifact.content_checksum = ChecksumURI(md5 if md5.startswith('md5:') else f'md5:{md5}')

    def _lookup_uri_and_meta(self, observation_id, plane, old_uri):
        # self._logger.error(plane.product_id)
        obs_bits = observation_id.split('-')
        skymap = obs_bits[0]
        plane_bits = plane.product_id.split('-')
        dataset_type = plane_bits[0]
        tract = plane_bits[1]
        patch = plane_bits[2]
        band = plane_bits[3]
        data_id = {
            'band': band,
            'skymap': skymap,
            'tract': tract,
            'patch': patch,
        }
        self._logger.debug(
            f'Looking up dataset_ref type={dataset_type} instrument={self.instrument} data_id={data_id}'
        )
        try:
            butler_uri = self.clients.butler.getURI(data_id)
        except Exception as e:
            raise CadcException(f'Butler getURI failed for {old_uri}: {e}') from e

        if butler_uri is None:
            raise CadcException(f'Butler getURI returned None for {old_uri}.')

        # url = butler_uri.geturl() if hasattr(butler_uri, 'geturl') else str(butler_uri)
        # new_uri = urllib.parse.urlsplit(url).path.replace(self.si_path_root, '')
        uri = butler_uri.get('uri')
        new_uri = uri.split('/raven/files/')[1]
        if not new_uri:
            raise CadcException(f'Butler getURI produced empty URI for {old_uri} from {new_uri}.')

        length = getattr(butler_uri, 'size', None)
        if length is None:
            length = getattr(butler_uri, 'content_length', None)
        md5 = getattr(butler_uri, 'md5', None) or getattr(butler_uri, 'checksum', None)
        if md5 is not None:
            md5 = str(md5)
        return new_uri, length, md5


def _coerce(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return value


def visit(observation, **kwargs):
    """Meta-visitor entrypoint used by caom2pipe META_VISITORS lists."""
    return XmlAugmentationVisitor(observation, **kwargs).visit()
