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

from ...datatypes.table import Table
from ..table_fns import TableExtract

import unittest


# --- unit tests
class RegTest(unittest.TestCase):
    def setUp(self):
        self.table_array = [
            ("foo", "boo", "goo"),
            (3.0, "a", 5),
            (1.0, "b", 6),
            (2.0, "c", 7),
        ]
        self.table = Table(self.table_array)

    def tearDown(self):
        # perform clean-up actions, if any
        pass

    def test_table_extract(self):
        ref_table = Table([
            ("foo", "boo"),
            (3.0, "a"),
            (1.0, "b"),
            (2.0, "c"),
        ])
        self.assertEqual(TableExtract(self.table, ["foo", "boo"]), ref_table)

if __name__ == "__main__":
    unittest.main()
