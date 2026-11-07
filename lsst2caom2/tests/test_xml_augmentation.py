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

import datetime
from unittest.mock import MagicMock, Mock

import pytest
from caom2 import Algorithm, Artifact, ChecksumURI, Plane, ProductType, ReleaseType, SimpleObservation
from caom2pipe.manage_composable import CadcException

from lsst2caom2 import xml_augmentation as xa


def _observation(obs_id='lsst_cells_v1-453-11', uri=None, length=None, md5=None, meta_release=None):
    if uri is None:
        uri = (
            'lsst:dp1/LSSTComCam/runs/DRP/DP1/DM-51335/deep_coadd/453/11/y/'
            'deep_coadd_453_11_y_lsst_cells_v1.fits'
        )
    observation = SimpleObservation(
        collection='LSST.DP1',
        observation_id=obs_id,
        algorithm=Algorithm('lsst.deep_coadd'),
    )
    observation.meta_release = meta_release
    plane = Plane('deep_coadd-453-11-y')
    artifact = Artifact(uri, ProductType.SCIENCE, ReleaseType.DATA)
    if length is not None:
        artifact.content_length = length
    if md5 is not None:
        artifact.content_checksum = ChecksumURI(md5 if md5.startswith('md5:') else f'md5:{md5}')
    plane.artifacts[uri] = artifact
    observation.planes['deep_coadd-453-11-y'] = plane
    return observation, uri


def _butler_uri(
    url='https://example.canfar.net/raven/files/lsst:dp1/rewritten/y.fits',
    size=12345,
    checksums=None,
):
    uri_info = MagicMock()
    uri_info.uri = url
    uri_info.size = size
    uri_info.checksums = checksums if checksums is not None else {'adler': 'uSXNuA=='}
    butler_uri = MagicMock()
    butler_uri.get_info.return_value = uri_info
    return butler_uri


def _clients(butler_uri_obj=None, dataset_ref=None):
    butler = MagicMock()
    ref = dataset_ref or MagicMock()
    ref.datasetType.name = 'deep_coadd'
    butler.find_dataset.return_value = ref
    butler.getURI.return_value = butler_uri_obj if butler_uri_obj is not None else _butler_uri()
    clients = Mock()
    clients.butler = butler
    return clients, butler, ref


def _lookup(**extra):
    lookup = {
        'dataset_type': 'deep_coadd',
        'instrument': 'LSSTCam',
        'observation_id_keys': ['skymap', 'tract'],
        'si_path_root': '/raven/files/',
        'butler_collections': 'LSSTCam/runs/DRP/DP2',
        'data_release': datetime.datetime(2024, 1, 15),
    }
    lookup.update(extra)
    return lookup


def test_rekey_artifact():
    plane = Plane('product')
    old_uri = 'cadc:XML/old.fits'
    new_uri = 'cadc:XML/new.fits'
    plane.artifacts[old_uri] = Artifact(old_uri, ProductType.SCIENCE, ReleaseType.DATA)
    artifact = xa.rekey_artifact(plane, old_uri, new_uri)
    assert old_uri not in plane.artifacts
    assert artifact.uri == new_uri
    assert plane.artifacts[new_uri] is artifact


def test_rekey_artifact_collision():
    plane = Plane('product')
    uri_a = 'cadc:XML/a.fits'
    uri_b = 'cadc:XML/b.fits'
    plane.artifacts[uri_a] = Artifact(uri_a, ProductType.SCIENCE, ReleaseType.DATA)
    plane.artifacts[uri_b] = Artifact(uri_b, ProductType.SCIENCE, ReleaseType.DATA)
    with pytest.raises(CadcException):
        xa.rekey_artifact(plane, uri_a, uri_b)


def test_rewrite_uri_and_fill_missing_meta(test_config):
    observation, old_uri = _observation()
    butler_uri = _butler_uri(
        url='https://example.canfar.net/raven/files/lsst:dp1/rewritten/y.fits',
        size=12345,
    )
    clients, butler, ref = _clients(butler_uri)
    test_config.lookup = _lookup()

    result = xa.visit(observation, config=test_config, clients=clients)

    assert result is observation
    plane = observation.planes['deep_coadd-453-11-y']
    assert old_uri not in plane.artifacts
    new_uri = 'lsst:dp1/rewritten/y.fits'
    artifact = plane.artifacts[new_uri]
    assert artifact.uri == new_uri
    assert artifact.content_length == 12345
    # Adler checksum application is currently disabled in xml_augmentation.
    assert artifact.content_checksum is None
    butler.find_dataset.assert_called_once_with(
        'deep_coadd',
        collections=['LSSTCam/runs/DRP/DP2'],
        band='y',
        skymap='lsst_cells_v1',
        tract=453,
        patch=11,
    )
    butler.getURI.assert_called_once_with(ref)


def test_rewrite_preserves_existing_length_checksum(test_config):
    observation, _ = _observation(length=999, md5='md5:alreadythere')
    butler_uri = _butler_uri(
        url='https://host/raven/files/cadc:NEW/file.fits',
        size=1,
        checksums={'adler': 'newchecksum'},
    )
    clients, _, _ = _clients(butler_uri)
    test_config.lookup = _lookup()

    xa.visit(observation, config=test_config, clients=clients)
    artifact = list(observation.planes['deep_coadd-453-11-y'].artifacts.values())[0]
    assert artifact.content_length == 999
    assert artifact.content_checksum.uri == 'md5:alreadythere'


def test_find_dataset_none_geturi_fails(test_config):
    observation, _ = _observation()
    clients, butler, _ = _clients()
    butler.find_dataset.return_value = None
    butler.getURI.side_effect = RuntimeError('not found')
    test_config.lookup = _lookup()
    with pytest.raises(CadcException) as exc:
        xa.visit(observation, config=test_config, clients=clients)
    assert 'getURI failed' in str(exc.value)


def test_geturi_failure_fails(test_config):
    observation, _ = _observation()
    clients, butler, _ = _clients()
    butler.getURI.side_effect = RuntimeError('not found')
    test_config.lookup = _lookup()
    with pytest.raises(CadcException) as exc:
        xa.visit(observation, config=test_config, clients=clients)
    assert 'getURI failed' in str(exc.value)


def test_plane_release_filled_when_missing(test_config):
    obs_meta = datetime.datetime(2025, 6, 30)
    observation, _ = _observation(meta_release=obs_meta)
    clients, _, _ = _clients()
    test_config.lookup = _lookup(data_release=datetime.datetime(2024, 1, 15))
    xa.visit(observation, config=test_config, clients=clients)
    plane = observation.planes['deep_coadd-453-11-y']
    assert plane.data_release == datetime.datetime(2024, 1, 15)
    assert plane.meta_release == obs_meta


def test_plane_release_preserves_existing(test_config):
    observation, _ = _observation(meta_release=datetime.datetime(2025, 6, 30))
    plane = observation.planes['deep_coadd-453-11-y']
    plane.data_release = datetime.datetime(2020, 1, 1)
    plane.meta_release = datetime.datetime(2021, 1, 1)
    clients, _, _ = _clients()
    test_config.lookup = _lookup(data_release=datetime.datetime(2024, 1, 15))
    xa.visit(observation, config=test_config, clients=clients)
    assert plane.data_release == datetime.datetime(2020, 1, 1)
    assert plane.meta_release == datetime.datetime(2021, 1, 1)


def test_plane_meta_release_falls_back_to_now(test_config):
    observation, _ = _observation(meta_release=None)
    clients, _, _ = _clients()
    test_config.lookup = _lookup()
    before = datetime.datetime.now()
    xa.visit(observation, config=test_config, clients=clients)
    meta_release = observation.planes['deep_coadd-453-11-y'].meta_release
    assert meta_release.tzinfo is None
    assert meta_release >= before - datetime.timedelta(seconds=5)


def test_yaml_date_coerced_to_naive_datetime(test_config):
    observation, _ = _observation()
    test_config.lookup = {
        'uri_rewrite_fields': ['plane_data_release'],
        'data_release': datetime.date(2025, 6, 30),
    }

    class Object:
        pass

    getURI_mock = Mock()
    clients_mock = Mock()
    clients_mock.butler.getURI.return_value = getURI_mock
    get_info_mock = Object()
    get_info_mock.uri = 'https://ws.cadc-ccda.hia-iha.nrc-cnrc.gc.ca/raven/files/lsst:dp1/LSSTComCam/runs/DRP/DP1/DM-51335/deep_coadd/453/11/g/deep_coadd_453_11_g_lsst_cells_v1_LSSTComCam_runs_DRP_DP1_DM-51335.fits'
    get_info_mock.size = 6
    get_info_mock.checksums = {
        'adler': 'uSXNuA==',
    }
    getURI_mock.get_info.return_value = get_info_mock

    xa.visit(observation, config=test_config, clients=clients_mock)
    assert observation.planes['deep_coadd-453-11-y'].data_release == datetime.datetime(2025, 6, 30)


def test_missing_data_release_fails_when_listed(test_config):
    observation, _ = _observation()
    test_config.lookup = {'butler_collections': 'LSSTCam/runs/DRP/DP2'}
    with pytest.raises(CadcException) as exc:
        xa.visit(observation, config=test_config, clients=Mock())
    assert "lookup['data_release'] is missing" in str(exc.value)
