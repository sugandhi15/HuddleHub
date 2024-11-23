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

from ..table import Table

import unittest
import pickle


# --- Unit tests
class RegTest(unittest.TestCase):
    def setUp(self):
        # --- perform set-up actions, if any
        self.list = [
            ("foo", "boo", "goo"),
            (3.0, "a", 5),
            (1.0, "b", 6),
            (2.0, "c", 7),
            (2.0, "d", 9),
        ]
        self.table = Table(self.list)

    def tearDown(self):
        # --- perform clean-up actions, if any
        pass

    def test_to_list(self):
        # --- NB: for proper comparison, each row of the table array must
        #         be converted to a tuple
        self.assertEqual([tuple(r) for r in self.table.to_list()], self.list)

    def test_len(self):
        self.assertEqual(len(self.table), len(self.list)-1)

    def test_getitem(self):
        self.assertEqual(self.table[1].goo, 6)
        self.assertEqual(self.table[1]["goo"], 6)

    def test_append(self):
        newrow = (4.0, "d", 8)
        self.list.append(newrow)
        self.table.append(newrow)
        self.assertEqual([tuple(r) for r in self.table.to_list()], self.list)

    def test_column(self):
        self.assertEqual(self.table.column("boo"), ["a", "b", "c", "d"])

    def test_find(self):
        self.assertEqual([row.values for row in self.table.find("foo", 2.0)],
                         [[2.0, "c", 7], [2.0, "d", 9]])

    def test_pickling(self):
        new_table = pickle.loads(pickle.dumps(self.table, 2))
        # --- check that the two tables are identical
        self.assertEqual(new_table, self.table)
        # --- check that data representations are identical
        self.assertEqual([tuple(r) for r in new_table.to_list()], self.list)
        # --- check that string representations are identical
        self.assertEqual(new_table.__str__(), self.table.__str__())

if __name__ == "__main__":
    unittest.main()
