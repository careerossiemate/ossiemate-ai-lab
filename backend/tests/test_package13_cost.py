import ast
import unittest
from pathlib import Path

# Isolate the pure parser from Azure and FastAPI dependencies; no cloud calls.
source=Path(__file__).resolve().parents[1]/'routers'/'package13.py'
node=next(n for n in ast.parse(source.read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='parse_cost')
ns={}
exec(compile(ast.Module(body=[node],type_ignores=[]),str(source),'exec'),ns)
parse=ns['parse_cost']
class CostTests(unittest.TestCase):
    def test_multiple_currencies(self):
        self.assertEqual(parse({'properties':{'columns':[{'name':'PreTaxCost'},{'name':'Currency'}],'rows':[[2,'AUD'],[3,'AUD'],[4,'USD']]}}),{'AUD':5,'USD':4})
    def test_empty(self):
        self.assertEqual(parse({'properties':{'columns':[{'name':'Cost'},{'name':'Currency'}],'rows':[]}}),{})
    def test_pagination(self):
        with self.assertRaises(ValueError): parse({'properties':{'nextLink':'next'}})
if __name__=='__main__': unittest.main()
