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


from collections import defaultdict

from caom2 import ProductType
from caom2pipe.manage_composable import StorageName
import logging


class LSSTName(StorageName):
    """
    Specialization of StorageName for LSST specifics.
    Implements cardinality rules for LSST data.
    """

    # TODO - testing to see if it's ok to set all the interesting values after StorageName construciton
    # e.g. in _set_preconditions
    # def __init__(self, obs_data_id, clients, dataset_type, instrument):
    #     """
    #     Keep the API for manage_composable.StorageName, but override with LSST-specific functionality.

    #     :param obs_data_id: dictionary of observation data id
    #     :param clients: clients ButlerClientCollection object
    #     :param dataset_type: dataset type string, value originates in Config.lookup
    #     :param instrument: instrument string, value originates in Config.lookup
    #     """
    #     # super().__init__(obs_id, product_id=None, file_name=None, source_names=None)
    #     self._obs_id = '-'.join([f'{obs_data_id[x]}' for x in obs_data_id])
    #     self.clients = clients
    #     self.dataset_type = dataset_type
    #     self.instrument = instrument
    #     self.dataset_refs = defaultdict(list)
    #     self.dataset_ref_key = None
    #     self.artifact_index = 0
    #     # self._product_id = None
    #     # self._file_name = None
    #     # self._source_names = []
    #     # # list of str - the Artifact URIs as represented at CADC. Sufficient
    #     # # for storing/retrieving to/from CADC.
    #     # self._destination_uris = []
    #     # # str - the file name with all file type and compression extensions removed
    #     # self._file_id = None
    #     # key is destination uri, value is file metadata, such as fits headers, db record, etc
    #     self._metadata = {}
    #     # key is destination uri, value is type FileInfo
    #     self._file_info = {}
    #     self._file_uri = None
    #     self._logger = logging.getLogger(self.__class__.__name__)

    # @property
    # def file_uri(self):
    #     uri = self.clients.butler.getURI(self.dataset_refs[self.dataset_ref_key][self.artifact_index])
    #     return uri.geturl().replace('/raven/files/', '')

    # def __str__(self):
    #     return (
    #         f'{super().__str__()}\n'
    #         f'    dataset_type: {self.dataset_type}\n'
    #         f'      instrument: {self.instrument}\n'
    #         f'    dataset_refs: {", ".join(ii for ii in self.dataset_refs.keys())}\n'
    #     )

    def is_valid(self):
        if self.file_name:
            return super().is_valid()
        return True


    def set_metadata(self):
        product_types = {
            f'{self.dataset_type}': ProductType.THIS,
            f'{self.dataset_type}_n_image': ProductType.AUXILIARY,
            f'{self.dataset_type}_background': ProductType.AUXILIARY,
        }
        plane_dataset_refs = self.clients.butler.query_datasets(self.dataset_type, self.instrument, self._obs_id)
        self._logger.error(plane_dataset_refs)
        for plane_dataset_ref in plane_dataset_refs:
            dataset_refs = self.clients.butler.query_all_datasets(plane_dataset_ref.data_id)
            for dataset_ref in dataset_refs:
                if dataset_ref.datasetType.name in product_types.keys():
                    band = plane_dataset_ref.dataId['band']
                    product_id = f'{self.dataset_type}-{band}'
                    if self.dataset_ref_key is None:
                        self.dataset_ref_key = product_id
                    self.dataset_refs[product_id].append(dataset_ref)
        # self.set_source_names()
        # self.set_destination_uris()
        # self.set_file_id()
        # self.set_obs_id()
        # self.set_product_ids()
        self._logger.debug(self)
