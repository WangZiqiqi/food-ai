from food_ai.enhanced_extractor_v3 import V3EntityNormalizer
from food_ai.enhanced_extractor_v3 import (
    EnhancedExtractorV3,
    _hydrate_extractor_from_graph,
    _resolve_article_for_extraction,
)
import networkx as nx


class FakeLLM:
    def __init__(self, responses):
        self.responses = list(responses)

    def extract_json(self, prompt, system_prompt=None, temperature=0.1, **kwargs):
        if not self.responses:
            raise AssertionError("Unexpected LLM call")
        return self.responses.pop(0)


class FakeEmbeddingClient:
    def __init__(self, vectors):
        self.vectors = vectors

    def embed(self, text):
        return self.vectors.get(text, [])


def test_entity_normalizer_merges_into_embedding_recalled_candidate():
    llm = FakeLLM([{"same_entity": True, "reasoning": "same food exposure"}])
    normalizer = V3EntityNormalizer(llm_client=llm)
    normalizer.embedding_client = FakeEmbeddingClient(
        {
            "kombucha": [1.0, 0.0],
            "kombucha tea": [0.99, 0.01],
        }
    )

    canonical_a, _ = normalizer.normalize_entity("kombucha", "food")
    canonical_b, _ = normalizer.normalize_entity("kombucha tea", "food")

    assert canonical_a == "kombucha"
    assert canonical_b == "kombucha"
    assert normalizer.stats["embedding_merges"] == 1


def test_entity_normalizer_keeps_distinct_entities_when_llm_rejects_merge():
    llm = FakeLLM([{"same_entity": False, "reasoning": "broader vs narrower"}])
    normalizer = V3EntityNormalizer(llm_client=llm)
    normalizer.embedding_client = FakeEmbeddingClient(
        {
            "mediterranean diet": [1.0, 0.0],
            "green-mediterranean diet": [0.95, 0.05],
        }
    )

    canonical_a, _ = normalizer.normalize_entity("mediterranean diet", "food")
    canonical_b, _ = normalizer.normalize_entity("green-mediterranean diet", "food")

    assert canonical_a == "mediterranean_diet"
    assert canonical_b == "green-mediterranean_diet"
    assert normalizer.stats["new_entities"] == 2


def test_hydrate_extractor_restores_missing_claim_merge_fields():
    extractor = EnhancedExtractorV3()
    extractor.embedding_client = None
    graph = nx.DiGraph()
    graph.add_node(
        "claim_1",
        node_type="claim",
        claim_id="claim_1",
        subject_name="yogurt",
        subject_type="food",
        object_name="cholesterol",
        object_type="outcome",
        direction="positive",
    )

    _hydrate_extractor_from_graph(extractor, graph)

    claim = extractor.claim_merger.claims_index["claim_1"]
    assert claim["merged_from"] == []
    assert claim["evidence_list"] == []
    assert claim["evidence_count"] == 0


def test_resolve_article_falls_back_to_selected_abstract():
    selected_article = {
        "pmid": " 12345\n",
        "title": "Selected title",
        "abstract": "Selected abstract",
        "study_type": "RCT",
    }

    article = _resolve_article_for_extraction(selected_article, {})

    assert article["pmid"] == "12345"
    assert article["title"] == "Selected title"
    assert article["abstract"] == "Selected abstract"


def test_resolve_article_prefers_metadata_text():
    selected_article = {
        "pmid": "12345",
        "title": "Selected title",
        "abstract": "Selected abstract",
    }
    all_articles = {
        "12345": {
            "pmid": "12345",
            "title": "Metadata title",
            "abstract": "Metadata abstract",
        }
    }

    article = _resolve_article_for_extraction(selected_article, all_articles)

    assert article["title"] == "Metadata title"
    assert article["abstract"] == "Metadata abstract"
