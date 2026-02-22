from __future__ import annotations

import io
from types import SimpleNamespace

from fastapi.testclient import TestClient
from PIL import Image

from app.presentation import api


class FakeQueue:
    def __init__(self) -> None:
        self.calls = []

    def enqueue(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return SimpleNamespace(id='job-123')


def _image_bytes() -> bytes:
    img = Image.new('RGB', (20, 20), 'white')
    out = io.BytesIO()
    img.save(out, format='PNG')
    return out.getvalue()


def test_health() -> None:
    client = TestClient(api.app)
    res = client.get('/api/health')
    assert res.status_code == 200
    assert res.json()['status'] == 'ok'


def test_enqueue_single_job(monkeypatch) -> None:
    fake = FakeQueue()
    monkeypatch.setattr(api, 'queue', fake)

    client = TestClient(api.app)
    res = client.post(
        '/api/jobs/remove-bg',
        files={'file': ('a.png', _image_bytes(), 'image/png')},
        data={'feather_radius': '0', 'alpha_boost': '1'},
    )

    assert res.status_code == 200
    body = res.json()
    assert body['job_id'] == 'job-123'
    assert fake.calls


def test_enqueue_rejects_non_image(monkeypatch) -> None:
    fake = FakeQueue()
    monkeypatch.setattr(api, 'queue', fake)

    client = TestClient(api.app)
    res = client.post(
        '/api/jobs/remove-bg',
        files={'file': ('a.txt', b'hello', 'text/plain')},
    )

    assert res.status_code == 400


def test_metrics_endpoint() -> None:
    client = TestClient(api.app)
    res = client.get('/api/metrics')
    assert res.status_code == 200
    assert 'timestamp' in res.json()


def test_cancel_job(monkeypatch) -> None:
    class DummyJob:
        id = 'job-x'

        def __init__(self) -> None:
            self._status = 'queued'

        def get_status(self, refresh=True):  # noqa: ARG002
            return self._status

        def cancel(self):
            self._status = 'canceled'

    monkeypatch.setattr(api.Job, 'fetch', lambda *args, **kwargs: DummyJob())  # noqa: ARG005
    client = TestClient(api.app)
    res = client.post('/api/jobs/job-x/cancel')
    assert res.status_code == 200
    assert res.json()['status'] == 'canceled'


def test_prometheus_metrics() -> None:
    client = TestClient(api.app)
    res = client.get('/api/metrics/prometheus')
    assert res.status_code == 200
    assert 'rmbg_' in res.text


def test_retry_failed_job(monkeypatch) -> None:
    class DummyJob:
        id = 'job-f'
        func_name = 'app.tasks.background_jobs.process_single_image_job'
        args = (b'abc', 'a.png', 0.0, 1.0)
        kwargs = {}

        def get_status(self, refresh=True):  # noqa: ARG002
            return 'failed'

    class DummyQueue:
        def enqueue_call(self, **kwargs):
            return SimpleNamespace(id='job-new')

    monkeypatch.setattr(api.Job, 'fetch', lambda *args, **kwargs: DummyJob())  # noqa: ARG005
    monkeypatch.setattr(api, 'queue', DummyQueue())
    client = TestClient(api.app)
    res = client.post('/api/jobs/job-f/retry')
    assert res.status_code == 200
    assert res.json()['job_id'] == 'job-new'
