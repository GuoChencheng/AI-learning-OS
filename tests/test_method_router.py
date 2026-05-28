from ailearn.method_router import recommend_methods
from ailearn.models import LearningState


def test_method_router_maps_formula_without_trust_to_derivation_work():
    recommendation = recommend_methods(LearningState.FORMULA_WITHOUT_TRUST)

    assert "derivation trust" in recommendation.actions
    assert "Socratic drill" in recommendation.actions
    assert recommendation.state == LearningState.FORMULA_WITHOUT_TRUST


def test_method_router_maps_too_much_material_to_goal_restructuring():
    recommendation = recommend_methods("too_much_material")

    assert "goal restructuring" in recommendation.actions
    assert "reference lookup" in recommendation.actions
    assert recommendation.state == LearningState.TOO_MUCH_MATERIAL
