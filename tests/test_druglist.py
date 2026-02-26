from claimguard.data.druglist import load_med_list, is_reimbursable


def test_load_med_list_cache(tmp_path, monkeypatch):
    # créer un petit pdf simulé en écriture (on ne fait que patcher extract_text)
    monkeypatch.setattr(
        "claimguard.data.druglist.extract_text",
        lambda p: "Aspirine\nParacétamol"
    )
    meds = load_med_list("dummy.pdf")
    assert "aspirine" in meds
    assert "paracétamol" in meds


def test_is_reimbursable(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "claimguard.data.druglist.load_med_list",
        lambda path=None: {"ibuprofene"}
    )
    assert is_reimbursable("ibuprofene")
    assert not is_reimbursable("autre")
