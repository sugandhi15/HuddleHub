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
from onyx.core.database.ufo_base import UfoBase
from onyx.core.database.ufo_fields import FieldError
from onyx.core.database.ufo_fields import StringField, SelectField, IntField
from onyx.core.database.ufo_fields import SelectIntField, FloatField, BoolField
from onyx.core.database.ufo_fields import DateField, SetField

import unittest

__all__ = []


class ufo_class(UfoBase):
    string_attr = StringField()
    string_attr_def = StringField(default="default string")
    select_attr = SelectField(options=["option1", "option2"])
    int_attr = IntField()
    int_attr_def = IntField(default=666)
    int_attr_pos = IntField(positive=True)
    select_int_attr = SelectIntField(options=[1, 2])
    float_attr = FloatField()
    float_attr_def = FloatField(default=666.666)
    float_attr_pos = FloatField(positive=True)
    bool_attr = BoolField()
    date_attr = DateField()
    set_attr = SetField()


# --- Unit tests
class RegTest(unittest.TestCase):
    def setUp(self):
        self.obj = ufo_class()

    def test_string(self):
        self.obj.string_attr = "a string"
        self.assertEqual(self.obj.string_attr_def, "default string")
        with self.assertRaises(FieldError):
            self.obj.string_attr = 123
        with self.assertRaises(FieldError):
            self.obj.string_attr = None

    def test_select(self):
        self.obj.select_attr = "option1"
        self.obj.select_attr = "option2"
        with self.assertRaises(FieldError):
            self.obj.select_attr = 123
        with self.assertRaises(FieldError):
            self.obj.select_attr = None
        with self.assertRaises(FieldError):
            self.obj.select_attr = "option3"

    def test_int(self):
        self.obj.int_attr = 123
        self.assertEqual(self.obj.int_attr_def, 666)
        with self.assertRaises(FieldError):
            self.obj.int_attr = "a string"
        with self.assertRaises(FieldError):
            self.obj.int_attr = 123.456
        with self.assertRaises(FieldError):
            self.obj.int_attr = None
        self.obj.int_attr_pos = 123
        with self.assertRaises(FieldError):
            self.obj.int_attr_pos = -123
        with self.assertRaises(FieldError):
            self.obj.int_attr_pos = 123.456
        with self.assertRaises(FieldError):
            self.obj.int_attr_pos = -123.456

    def test_select_int(self):
        self.obj.select_int_attr = 1
        self.obj.select_int_attr = 2
        with self.assertRaises(FieldError):
            self.obj.select_int_attr = "abc"
        with self.assertRaises(FieldError):
            self.obj.select_int_attr = 1.0
        with self.assertRaises(FieldError):
            self.obj.select_int_attr = None
        with self.assertRaises(FieldError):
            self.obj.select_int_attr = 3

    def test_float(self):
        self.obj.float_attr = 123.456
        self.assertEqual(self.obj.float_attr_def, 666.666)
        with self.assertRaises(FieldError):
            self.obj.float_attr = "a string"
        with self.assertRaises(FieldError):
            self.obj.float_attr = 123
        with self.assertRaises(FieldError):
            self.obj.float_attr = None
        self.obj.float_attr_pos = 123.456
        with self.assertRaises(FieldError):
            self.obj.float_attr_pos = -123.456
        with self.assertRaises(FieldError):
            self.obj.float_attr_pos = 123
        with self.assertRaises(FieldError):
            self.obj.float_attr_pos = -123

    def test_bool(self):
        self.obj.bool_attr = True
        self.obj.bool_attr = False
        with self.assertRaises(FieldError):
            self.obj.bool_attr = 0
        with self.assertRaises(FieldError):
            self.obj.bool_attr = None

    def test_date(self):
        cls = self.obj.__class__
        d = Date.today()
        self.obj.date_attr = d
        with self.assertRaises(FieldError):
            self.obj.date_attr = "abc"
        self.assertEqual(d, cls.date_attr.from_json(cls.date_attr.to_json(d)))

    def test_set(self):
        cls = self.obj.__class__
        s = {1, 2, 3, "a," "b", True}
        self.assertEqual(s, cls.set_attr.from_json(cls.set_attr.to_json(s)))


if __name__ == "__main__":
    unittest.main()
