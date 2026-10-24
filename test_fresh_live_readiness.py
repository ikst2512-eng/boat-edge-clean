from fresh_live_readiness import evaluate

def run():
    blocked={"formalFirst100":{"races":0},"connected":False,"predictions_ready":False,
             "guards":{"results_seen":False,"unlock":False,"scoring":False,"RESULT_UNLOCK_TOKEN":None}}
    result=evaluate(blocked,True)
    assert result["receiver_installed"] is True
    assert result["pre_result_collection_allowed"] is True
    assert result["formal_source_approved"] is False
    assert result["ready_to_send_real_candidate"] is False
    assert "external_v5_original_not_supplied" in result["blockers"]
    assert "formal_parent_not_approved" in result["blockers"]
    denied={**blocked,"guards":{**blocked["guards"],"results_seen":True}}
    assert evaluate(denied,True)["pre_result_collection_allowed"] is False
    assert "receiver_missing_on_main" in evaluate(blocked,False)["blockers"]
    print("Read-only readiness correctly blocks unverified real predictions")
if __name__=="__main__":run()
