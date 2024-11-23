###############################################################################
#
#   Copyright: (c) 2015 Carlo Sbraccia
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
###############################################################################

from onyx.core.datatypes.date import Date
from onyx.core.database.objdb import ObjDbDummyClient, ObjNotFound
from onyx.core.database.test import ufo_testcls

import unittest


# --- Unit tests
class RegTest(unittest.TestCase):
    def test_add_get_update_delete(self):
        clt = ObjDbDummyClient("dummy_db", "dummy_user")
        obj = ufo_testcls.ufocls(Name="test")

        self.assertRaises(ObjNotFound, clt.get, obj.Name)
        self.assertEqual(clt.add(obj), obj)
        self.assertEqual(clt.get(obj.Name), obj)

        obj.Birthday = Date.today()
        self.assertEqual(clt.update(obj), obj)

        clt.delete(obj)
        self.assertRaises(ObjNotFound, clt.get, obj.Name)

if __name__ == "__main__":
    unittest.main()
