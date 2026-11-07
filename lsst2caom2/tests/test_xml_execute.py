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


import os
import types
from unittest.mock import Mock

import pytest
from caom2 import Algorithm, Artifact, Plane, ProductType, ReleaseType, SimpleObservation
from caom2pipe.manage_composable import CadcException, ExecutionReporter2, StorageName, TaskType, write_obs_to_file

from lsst2caom2.xml_execute import XmlIngestRunnerMeta, XmlOrganizeExecutesRunnerMeta


def _ensure_workspace(config, storage_name):
    working_dir = os.path.join(config.working_directory, storage_name.name)
    os.makedirs(working_dir, exist_ok=True)
    return working_dir


def _write_valid_observation(fqn, obs_id='test_obs_id', artifact_uri='cadc:XML/test.fits'):
    observation = SimpleObservation(
        collection='LSST.DP1',
        observation_id=obs_id,
        algorithm=Algorithm('exposure'),
    )
    plane = Plane('product')
    plane.artifacts[artifact_uri] = Artifact(artifact_uri, ProductType.SCIENCE, ReleaseType.DATA)
    observation.planes['product'] = plane
    write_obs_to_file(observation, fqn)
    return observation


def test_organize_chooses_xml_ingest(test_config, tmp_path):
    test_config.change_working_directory(tmp_path.as_posix())
    test_config.task_types = [TaskType.VISIT]
    reporter = ExecutionReporter2(test_config)
    organizer = XmlOrganizeExecutesRunnerMeta(test_config, [], [], clients=Mock(), reporter=reporter)
    assert len(organizer._executors) == 1
    assert isinstance(organizer._executors[0], XmlIngestRunnerMeta)


def test_organize_rejects_unsupported_task(test_config, tmp_path):
    test_config.change_working_directory(tmp_path.as_posix())
    test_config.task_types = [TaskType.STORE]
    reporter = ExecutionReporter2(test_config)
    with pytest.raises(CadcException) as exc:
        XmlOrganizeExecutesRunnerMeta(test_config, [], [], clients=Mock(), reporter=reporter)
    assert 'does not support task type' in str(exc.value)


def test_ingest_happy_path(test_config, tmp_path):
    test_config.change_working_directory(tmp_path.as_posix())
    test_config.log_to_file = True
    os.makedirs(test_config.log_file_directory, exist_ok=True)
    # XML must not sit at working_directory/<name>: StorageName.name keeps the
    # .xml extension, and the executor creates that path as a workspace directory.
    xml_dir = tmp_path / 'incoming'
    xml_dir.mkdir()
    xml_fqn = (xml_dir / 'incoming.xml').as_posix()
    _write_valid_observation(xml_fqn, obs_id='real_obs_id')

    storage_name = StorageName(source_names=[xml_fqn])
    clients = Mock()
    clients.metadata_client.read.return_value = None
    subject = XmlIngestRunnerMeta(clients, test_config, [], ExecutionReporter2(test_config))
    _ensure_workspace(test_config, storage_name)
    subject.execute({'storage_name': storage_name})

    assert storage_name.obs_id == 'real_obs_id'
    assert subject._observation.observation_id == 'real_obs_id'
    assert subject._model_fqn == os.path.join(test_config.log_file_directory, 'real_obs_id.xml')
    assert os.path.exists(subject._model_fqn)


def test_meta_visitor_runs(test_config, tmp_path):
    test_config.change_working_directory(tmp_path.as_posix())
    test_config.log_to_file = False
    xml_dir = tmp_path / 'incoming'
    xml_dir.mkdir()
    xml_fqn = (xml_dir / 'visit.xml').as_posix()
    _write_valid_observation(xml_fqn, obs_id='visit_obs', artifact_uri='cadc:XML/old.fits')

    visited = {}

    def _visit(observation, **kwargs):
        from lsst2caom2.xml_augmentation import rekey_artifact

        plane = list(observation.planes.values())[0]
        old = list(plane.artifacts.keys())[0]
        rekey_artifact(plane, old, 'cadc:XML/new.fits')
        visited['done'] = True
        return observation

    clients = Mock()
    clients.metadata_client.read.return_value = None
    subject = XmlIngestRunnerMeta(
        clients, test_config, [types.SimpleNamespace(visit=_visit)], ExecutionReporter2(test_config)
    )
    storage_name = StorageName(source_names=[xml_fqn])
    _ensure_workspace(test_config, storage_name)
    subject.execute({'storage_name': storage_name})
    assert visited.get('done')
    assert 'cadc:XML/new.fits' in list(subject._observation.planes.values())[0].artifacts
