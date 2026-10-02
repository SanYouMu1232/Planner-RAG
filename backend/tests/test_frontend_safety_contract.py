from pathlib import Path
ROOT = Path(__file__).parents[2] / 'src'

def test_modal_backdrops_do_not_bind_close_handlers():
    targets = ['ApiConfigModal.tsx','UploadModal.tsx','DocumentDrawer.tsx','CreateProjectModal.tsx','RenameProjectModal.tsx','ResearchDrawer.tsx','SummaryDrawer.tsx']
    for name in targets:
        content = (ROOT/'components'/name).read_text(encoding='utf-8')
        assert 'absolute inset-0 bg-black/40" onClick' not in content
        assert 'fixed inset-0 z-40 bg-black/30" onClick' not in content

def test_frontend_has_streaming_and_cancellable_upload_paths():
    api = (ROOT/'api'/'client.ts').read_text(encoding='utf-8')
    upload = (ROOT/'components'/'UploadModal.tsx').read_text(encoding='utf-8')
    workbench = (ROOT/'pages'/'Workbench.tsx').read_text(encoding='utf-8')
    assert 'streamMessage' in api and 'answer.delta' in api
    assert 'uploadFileResumable' in api and '/cancel' in api
    assert '中断上传' in upload
    assert 'MarkdownAnswer' in workbench
