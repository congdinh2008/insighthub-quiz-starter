import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from run_aev import check_response

class EvaluationOracleTests(unittest.TestCase):
    def check(self,response,source=None):
        case={'sources':['test.txt'],'expected_status':'Answered','expected_evidence':[{'source':'test.txt','locator':{'type':'paragraph','value':'1'},'required_facts':['BLUE-17']}]}
        return check_response(case,response,200,{'test.txt':1},lambda _: (200,source or {'content':'Release BLUE-17','locator':{'type':'paragraph','value':'1'}}))[0]
    def response(self):
        return {'status':'Answered','answer':'BLUE-17','claims':[{'text':'BLUE-17','citation_ids':['chunk:1']}],'citations':[{'citation_id':'chunk:1','document_id':1,'source':'test.txt','locator':{'type':'paragraph','value':'1'},'excerpt':'Release BLUE-17'}],'latency_ms':1}
    def test_empty_claims_cannot_pass(self):
        response=self.response();response['claims']=[]
        self.assertFalse(self.check(response)['claim_references'])
    def test_fabricated_citation_and_wrong_source_fail(self):
        response=self.response();response['claims'][0]['citation_ids']=['chunk:missing']
        self.assertFalse(self.check(response)['claim_references'])
        response=self.response();response['citations'][0]['excerpt']='invented'
        self.assertFalse(self.check(response)['source_links'])
    def test_expected_location_and_fact_are_checked(self):
        self.assertTrue(all(self.check(self.response()).values()))
        self.assertFalse(self.check(self.response(),{'content':'unrelated','locator':{'type':'page','value':'9'}})['expected_sources'])

if __name__=='__main__':unittest.main()
