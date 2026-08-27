import json
import pytest

def events():
    return [{"step":0,"type":"user","payload":{"text":"go"}},{"step":1,"type":"tool","payload":{"name":"add"}}]

def test_round_trip_and_count(submission,tmp_path):
    path=tmp_path/"trajectory.jsonl"; assert submission.TrajectoryJsonl.write(path,events())==2
    assert list(submission.TrajectoryJsonl.read(path))==events()

def test_physical_order_and_compact_lines(submission,tmp_path):
    path=tmp_path/"t.jsonl"; submission.TrajectoryJsonl.write(path,events()); lines=path.read_text(encoding="utf-8").splitlines()
    assert [json.loads(line)["step"] for line in lines]==[0,1] and all(": " not in line for line in lines)

def test_reader_is_lazy_iterator(submission,tmp_path):
    path=tmp_path/"t.jsonl"; path.write_text('{"step":0,"type":"x","payload":{}}\n',encoding="utf-8")
    reader=submission.TrajectoryJsonl.read(path)
    assert iter(reader) is reader and next(reader)["step"]==0

@pytest.mark.parametrize("bad", [[{"step":1,"type":"x","payload":{}}],[{"step":0,"type":"","payload":{}}],[{"step":0,"type":"x","payload":[]}],[{"step":True,"type":"x","payload":{}}]])
def test_writer_rejects_invalid_event_without_success(submission,tmp_path,bad):
    with pytest.raises(ValueError): submission.TrajectoryJsonl.write(tmp_path/"bad.jsonl",bad)

@pytest.mark.parametrize("text", ['\n','[1]\n','{"step":0,"type":"x","payload":{}}\n{"step":2,"type":"x","payload":{}}\n'])
def test_reader_rejects_invalid_physical_stream(submission,tmp_path,text):
    path=tmp_path/"bad.jsonl"; path.write_text(text,encoding="utf-8")
    with pytest.raises(ValueError): list(submission.TrajectoryJsonl.read(path))

def test_write_does_not_mutate_events(submission,tmp_path):
    source=events(); before=json.loads(json.dumps(source)); submission.TrajectoryJsonl.write(tmp_path/"x.jsonl",source)
    assert source==before

