import unittest
from inspect_exhibition import inspect,Tables
class SchemaTests(unittest.TestCase):
    def test_six_rows_are_not_automatically_verified(self):
        page="<table><tr><th>展示タイム</th></tr>"+"".join(f"<tr><td>{i}</td><td>6.7</td></tr>" for i in range(1,7))+"</table>"
        result=inspect(page.encode())
        self.assertEqual(result["table_count"],1)
        self.assertEqual(result["rows"],7)
        self.assertFalse(result["accepted_as_model_input"])
    def test_nested_text_and_empty(self):
        p=Tables();p.feed("<table><tr><td>進入 <span>1</span></td></tr></table>")
        self.assertEqual(p.tables[0][0][0],"進入 1")
        self.assertEqual(inspect(b"<html></html>")["table_count"],0)
if __name__=="__main__":unittest.main()
