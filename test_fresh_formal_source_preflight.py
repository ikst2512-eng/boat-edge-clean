from fresh_formal_source_preflight import assess

def check():
    status={"guards":{"results_seen":False,"unlock":False,"scoring":False,"RESULT_UNLOCK_TOKEN":None},
            "formalFirst100":{"races":0,"freezeManifestSha":None},
            "connected":False,"predictions_ready":False}
    assert assess(status)=={"ready":False,"reason":"FORMAL_FIRST100_NOT_FROZEN"}
    status["formalFirst100"]={"races":100,"freezeManifestSha":"a"*64}
    assert assess(status)["reason"]=="APPROVED_MODEL_NOT_CONNECTED"
    status["connected"]=True;status["predictions_ready"]=True
    assert assess(status)["reason"]=="APPROVED_PREDICTION_HASHES_NOT_COMPLETE"
    status["approved_prediction_sha256_by_race"]={str(i):"a"*64 for i in range(100)}
    assert assess(status)["ready"] is True
    status["guards"]["scoring"]=True
    assert assess(status)["reason"]=="FORMAL_GUARDS_NOT_CLOSED"
    print("Formal upstream readiness preflight tests passed")

if __name__=="__main__":check()
