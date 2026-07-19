from __future__ import annotations

import json, subprocess, sys
from pathlib import Path
from unittest.mock import patch

from helpers import TempRepository, run_cli
from neo.domain.days import create_day
from neo.workspace import commit_workspace, _git_commit


def test_migrate_adds_medications_idempotent_and_preserves_existing():
    repo=TempRepository(Path(__file__).resolve().parents[1])
    try:
        d=create_day('2026-07-01T09:00:00+09:00'); d.pop('medications'); d['schema_version']=1
        p=repo.paths.days/'2026'/'2026-07-01.json'; p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(d,ensure_ascii=False))
        r=run_cli(repo.root,'--json','migrate'); assert r.returncode==0, r.stderr
        data=json.loads(p.read_text())
        # schema v2: empty medications stays empty (no placeholders)
        assert data['medications']==[]
        assert data['schema_version']==2
        before=p.read_text(); r=run_cli(repo.root,'--json','migrate'); assert r.returncode==0; assert p.read_text()==before
        # Placeholder (taken=false, note=None) should be removed during migration
        data['medications']=[{'name':'Custom','taken':False,'taken_at':None,'note':None}]; data['schema_version']=1; p.write_text(json.dumps(data,ensure_ascii=False))
        r=run_cli(repo.root,'--json','migrate'); assert r.returncode==0
        assert json.loads(p.read_text())['medications']==[]
    finally: repo.close()


def test_wake_medications_empty_and_take_new_day():
    repo=TempRepository(Path(__file__).resolve().parents[1])
    try:
        r=run_cli(repo.root,'--json','day','wake','--at','2026-07-02T09:00:00+09:00'); assert r.returncode==0, r.stderr
        data=json.loads((repo.paths.days/'2026'/'2026-07-02.json').read_text())
        # schema v2: new day starts with empty medications (no placeholders)
        assert data['medications']==[]
        # take works — appends a new event
        r=run_cli(repo.root,'--json','day','med','take','--name','약 A','--at','2026-07-02T10:00:00+09:00'); assert r.returncode==0, r.stderr
        resp=json.loads(r.stdout)
        assert 'medication_id' in resp
        data2=json.loads((repo.paths.days/'2026'/'2026-07-02.json').read_text())
        assert len(data2['medications'])==1
        assert data2['medications'][0]['name']=='약 A'
        assert data2['medications'][0]['action']=='taken'
    finally: repo.close()


def test_doctor_runs_and_reports_migration_needed():
    repo=TempRepository(Path(__file__).resolve().parents[1])
    try:
        d=create_day('2026-07-01T09:00:00+09:00'); d.pop('medications'); d['schema_version']=1
        p=repo.paths.days/'2026'/'2026-07-01.json'; p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(d,ensure_ascii=False))
        r=run_cli(repo.root,'--json','doctor'); assert r.returncode==0
        out=json.loads(r.stdout); assert out['migration_needed']
    finally: repo.close()


def test_message_log_invalid_and_no_day_required():
    repo=TempRepository(Path(__file__).resolve().parents[1])
    try:
        r=run_cli(repo.root,'--json','message','log','--role','user','--content','hi','--at','2026-07-05T05:58:20+09:00'); assert r.returncode==0, r.stderr
        assert (repo.root/'data/message-log/2026-07-05.jsonl').exists()
        r=run_cli(repo.root,'--json','message','log','--role','user','--content','hi','--at','not-a-date'); assert r.returncode!=0
        assert not list((repo.root/'data/days').glob('*/*.json'))
    finally: repo.close()


def test_fridge_categories_include_canonical():
    from neo.domain.fridge import CATEGORIES
    assert {'vegetable','meat','seafood','grain'} <= CATEGORIES


def test_last_push_status_written_on_failure():
    repo=TempRepository(Path(__file__).resolve().parents[1])
    subprocess.run(['git','init','-b','main'],cwd=repo.root,capture_output=True,check=True)
    subprocess.run(['git','config','user.email','t@example.com'],cwd=repo.root,capture_output=True,check=True)
    subprocess.run(['git','config','user.name','T'],cwd=repo.root,capture_output=True,check=True)
    try:
        p=repo.root/'brief.md'; p.write_text('x')
        _git_commit(repo.paths,[p],set())
        status=json.loads(repo.paths.last_push.read_text())
        assert status['success'] is False and status['remote']=='origin'
    finally: repo.close()
