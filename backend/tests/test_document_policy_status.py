import pytest


async def upload_document(client, **metadata):
    response = await client.post(
        '/api/documents/upload',
        files={'files': ('人口规划.txt', '规划常住人口为31400人。'.encode(), 'text/plain')},
        data=metadata,
    )
    assert response.status_code == 201
    return response.json()[0]


@pytest.mark.asyncio
@pytest.mark.parametrize('field', ['policy_status', 'policyStatus'])
@pytest.mark.parametrize('status', ['active', 'repealed', 'draft', 'unknown'])
async def test_policy_status_persists_without_reparsing(client, field, status):
    doc = await upload_document(client)
    before = (await client.get(f"/api/documents/{doc['id']}/chunks")).json()
    response = await client.patch(f"/api/documents/{doc['id']}", json={field: status})
    assert response.status_code == 200
    assert response.json()['policyStatus'] == status
    persisted = (await client.get(f"/api/documents/{doc['id']}")).json()
    assert persisted['policyStatus'] == status
    assert persisted['fileName'] == doc['fileName']
    assert persisted['parseStatus'] == doc['parseStatus']
    after = (await client.get(f"/api/documents/{doc['id']}/chunks")).json()
    assert before == after
    listing = (await client.get('/api/documents')).json()
    assert next(item for item in listing if item['id'] == doc['id'])['policyStatus'] == status


@pytest.mark.asyncio
@pytest.mark.parametrize('invalid', ['有效', 'deleted', ''])
async def test_invalid_policy_status_is_rejected_without_mutation(client, invalid):
    doc = await upload_document(client)
    response = await client.patch(f"/api/documents/{doc['id']}", json={'policy_status': invalid})
    assert response.status_code == 422
    current = (await client.get(f"/api/documents/{doc['id']}")).json()
    assert current['policyStatus'] == 'unknown'


@pytest.mark.asyncio
async def test_policy_status_only_changes_selected_document_and_reaches_new_citations(client):
    project = (await client.post('/api/projects', json={'name': '效力状态测试'})).json()
    doc = await upload_document(client, knowledge_base='project', project_id=project['id'])
    general = await upload_document(client, knowledge_base='general')
    updated = await client.patch(f"/api/documents/{doc['id']}", json={'policy_status': 'repealed'})
    assert updated.status_code == 200
    assert (await client.get(f"/api/documents/{general['id']}")).json()['policyStatus'] == 'unknown'
    conversation = (await client.post(f"/api/projects/{project['id']}/conversations", json={'title': '人口'})).json()
    response = await client.post(f"/api/conversations/{conversation['id']}/messages", json={'question': '人口', 'knowledge_source': 'project'})
    assert response.status_code == 201
    assert response.json()['citations']
    assert all(citation['policyStatus'] == 'repealed' for citation in response.json()['citations'])
    assert (await client.patch('/api/documents/nonexistent', json={'policyStatus': 'active'})).status_code == 404
