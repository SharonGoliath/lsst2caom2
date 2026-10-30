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


"""Execute specializations for loading Observation XML and running visitors."""

import logging
import os

from caom2pipe import execute_composable as ec
from caom2pipe import manage_composable as mc


__all__ = ['XmlIngestRunnerMeta', 'XmlOrganizeExecutesRunnerMeta']


class XmlIngestRunnerMeta(ec.CaomExecuteRunnerMeta):
    """Load an Observation from XML, run meta visitors, write the model.

    Does not use FITS-oriented MetaVisit preconditions.
    """

    def __init__(self, clients, config, meta_visitors, reporter):
        super().__init__(clients, config, meta_visitors, reporter)
        self._logger = logging.getLogger(self.__class__.__name__)

    def _set_preconditions(self):
        self._logger.debug(f'Begin _set_preconditions for {self._storage_name.file_name}')
        xml_fqn = self._storage_name.source_names[0]
        self._logger.debug(f'read Observation XML from {xml_fqn}')
        self._observation = mc.read_obs_from_file(xml_fqn)
        # Identity comes only from the Observation document.
        self._storage_name.obs_id = self._observation.observation_id
        # Recompute after obs_id is known; name (and therefore model_file_name) uses obs_id.
        if self._config.log_to_file:
            self._model_fqn = os.path.join(self._config.log_file_directory, self._storage_name.model_file_name)
        self._logger.debug('End _set_preconditions')

    def execute(self, context):
        self._logger.debug('Begin XmlIngestRunnerMeta.execute')
        super().execute(context)

        self._logger.debug('the metadata visitors')
        self._visit_meta()

        self._logger.debug('write the Observation XML for debugging')
        self._write_model()

        self._logger.debug('store the xml')
        self._caom2_store()

        self._logger.debug('End XmlIngestRunnerMeta.execute')


class XmlOrganizeExecutesRunnerMeta(ec.OrganizeExecutesRunnerMeta):
    """Choose XmlIngestRunnerMeta for VISIT instead of MetaVisitRunnerMeta."""

    def _choose(self):
        for task_type in self.task_types:
            if task_type == mc.TaskType.VISIT:
                self._logger.debug(f'Choosing executor XmlIngestRunnerMeta for {task_type}.')
                self._executors.append(
                    XmlIngestRunnerMeta(self._clients, self.config, self._meta_visitors, self._reporter)
                )
            else:
                raise mc.CadcException(
                    f'lsst2caom2 XML ingest does not support task type {task_type}; use visit only.'
                )
