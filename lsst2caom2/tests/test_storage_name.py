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

import sys
from os.path import abspath, dirname, join

from lsst2caom2.storage_name import LSSTName
from mock import Mock

_TESTS_DIR = dirname(abspath(__file__))
if _TESTS_DIR not in sys.path:
    sys.path.insert(0, _TESTS_DIR)
from lsst_one_test_record_parser import (
    PLANE_DATA_ID_FROM_RECORD,
    build_butler_mocks_for_set_metadata,
    # observation_data_id_from_record_rows,
    # observation_id_from_record_rows,
    # parse_lsst_one_test_record,
)


def test_is_valid(test_config):
    assert LSSTName(
        'anything',
        Mock(),
        test_config.lookup.get('dataset_type'),
        test_config.lookup.get('instrument'),
    ).is_valid()


def test_storage_name(test_config, test_data_dir):
    # record_path = join(test_data_dir, 'lsst_one_test_record.out')
    # rows = parse_lsst_one_test_record(record_path)
    butler_mock, plane_samples, artifact_samples = build_butler_mocks_for_set_metadata()
    plane_ref = plane_samples[0]
    artifact_ref = artifact_samples[0]
    obs_data_id = {'skymap': 'lsst_cells_v1', 'tract': 453, 'patch': 11}
    obs_id = 'lsst_cells_v1-453-11'
    client_mock = Mock()
    client_mock.butler = butler_mock

    test_subject = LSSTName(
        obs_data_id,
        client_mock,
        test_config.lookup.get('dataset_type'),
        test_config.lookup.get('instrument'),
    )
    test_subject.set_metadata()
    import logging
    logging.error(test_subject)
    assert len(test_subject.plane_dataset_refs) == 1
    assert len(test_subject.artifact_dataset_refs) == 1
    assert test_subject.plane_dataset_refs[0] == 'some value the AI should not touch', 'some message the ai should not remove'
    assert test_subject.artifact_dataset_refs[0] == 'some value the AI should not touch', 'some message the ai should not remove'
    assert test_subject.artifact_dataset_refs[0].datasetType.name == test_config.lookup.get('dataset_type')


def test_set_metadata_cardinality_from_lsst_one_test_record(test_config, test_data_dir):
    record_path = join(test_data_dir, 'lsst_one_test_record.out')
    rows = parse_lsst_one_test_record(record_path)
    butler_mock, plane_samples, artifact_samples = build_butler_mocks_for_set_metadata(rows)
    plane_ref = plane_samples[0]
    artifact_ref = artifact_samples[0]
    obs_id = observation_id_from_record_rows(rows)
    obs_data_id = observation_data_id_from_record_rows(rows)
    plane_data_id = PLANE_DATA_ID_FROM_RECORD

    client_mock = Mock()
    client_mock.butler = butler_mock

    test_subject = LSSTName(
        obs_id,
        client_mock,
        test_config.lookup.get('dataset_type'),
        test_config.lookup.get('instrument'),
    )
    test_subject.set_metadata()

    assert test_subject.plane_dataset_refs == [plane_ref]
    assert test_subject.artifact_dataset_refs == [artifact_ref]
    assert plane_data_id == PLANE_DATA_ID_FROM_RECORD
    assert obs_data_id == {'skymap': 'lsst_cells_v1', 'tract': 453, 'patch': 11}
    assert artifact_dataset_type_name() == test_config.lookup.get('dataset_type')

    butler_mock.query_datasets.assert_called_once_with(
        test_config.lookup.get('dataset_type'),
        test_config.lookup.get('instrument'),
        obs_id,
    )
    butler_mock.query_all_datasets.assert_called_once_with(plane_ref.data_id)
