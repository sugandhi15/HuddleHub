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
from onyx.core.database.objdb import ObjNotFound
from onyx.core.database.objdb_api import AddObj, GetObj, UpdateObj, DelObj
from onyx.core.database.objdb_api import ExistsInDatabase
from onyx.core.database.test import ufo_testcls
from onyx.core.utils.unittest import ObjDbTestCase

import unittest


# --- test API with the postgres client on TestDb
class Test_Postgres(ObjDbTestCase):
    def setUp(self):
        super().setUp()
        self.obj = ufo_testcls.ufocls(Name="test")

    def test_add_get_update_delete(self):
        self.assertRaises(ObjNotFound, GetObj, self.obj.Name, False)
        self.assertEqual(AddObj(self.obj), self.obj)

        self.assertEqual(GetObj(self.obj.Name, True), self.obj)
        self.assertEqual(GetObj(self.obj.Name, True).Birthday,
                         self.obj.Birthday)
        self.assertEqual(GetObj(self.obj.Name, True).OtherDates,
                         self.obj.OtherDates)
        self.assertEqual(GetObj(self.obj.Name, True).SimpleCurve,
                         self.obj.SimpleCurve)

        self.obj.Birthday = Date.now()
        self.assertEqual(UpdateObj(self.obj), self.obj)

        self.assertEqual(GetObj(self.obj.Name, True), self.obj)

        DelObj(self.obj)
        self.assertRaises(ObjNotFound, GetObj, self.obj.Name)

    def test_exists(self):
        self.assertFalse(ExistsInDatabase(self.obj.Name))
        AddObj(self.obj)
        self.assertTrue(ExistsInDatabase(self.obj.Name))
        DelObj(self.obj)
        self.assertFalse(ExistsInDatabase(self.obj.Name))


if __name__ == "__main__":
    from onyx.core.utils.unittest import UseEphemeralDbs
    with UseEphemeralDbs():
        unittest.main(failfast=True)
