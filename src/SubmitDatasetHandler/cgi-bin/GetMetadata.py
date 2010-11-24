#!/usr/bin/python
#
# Coypyright (C) 2010, University of Oxford
#
# Licensed under the MIT License.  You may obtain a copy of the License at:
#
#     http://www.opensource.org/licenses/mit-license.php
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# $Id: $

"""
Data submission Handler program for populating metadata for the requested dataset
"""
__author__ = "Bhavana Ananda"
__version__ = "0.1"

import cgi, sys, logging, os, os.path,traceback, rdflib
from rdflib.graph import Graph

sys.path.append("..")
sys.path.append("../..")

import ManifestRDFUtils
from MiscLib import TestUtils

ZipMimeType  =  "application/zip"
FilePat      =  re.compile("^.*$(?<!\.zip)")
logger       =  logging.getLogger("GetMetadata")

ElementCreator     =  "creator"
ElementIdentifier  =  "identifier"
ElementTitle       =  "title"
ElementDescription =  "description"
ElementList        =  [ElementCreator,ElementIdentifier,ElementTitle,ElementDescription]  

def getMetadata(formdata, basedir, outputstr):
    """
    Gets the metadata from the manifest.rdf file and formulates it into the JSON format.
    
    formdata    is a dictionary containing parameters from the dataset submission form
    """
    dirName     = SubmitDatasetUtils.getFormParam("directory",formdata)
    
    outputstr.write("Content-type: application/JSON\n")
    outputstr.write("\n")      # end of MIME headers

    dirs = getManifestRDFAsJsonFromDirectory(dirName , basedir)

    #result = json.dumps(dirs)
    #outputstr.write(result)

    json.dump(dirs, outputstr, indent=4)

    return




if __name__ == "__main__":
    form = cgi.FieldStorage()   # Parse the query
    os.chdir("/home")           # Base directory for admiral server data
    
    getMetadata(form,"/home/data", "/home", sys.stdout)

# End.