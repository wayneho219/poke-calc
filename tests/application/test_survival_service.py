from domain.models.nature import NatureRegistry
from domain.models.stats import StatSet
from domain.models.pokemon import Pokemon
from application.calculator import StatCalculator
from application.survival_service import SurvivalService, AttackInput

NEUTRAL = NatureRegistry.get_by_name("Hardy")

def make_pokemon(base_hp: int, base_def: int) -> Pokemon:
    return Pokemon(
        id=1, name_en="Test", name_zh="測試", name_ja="テスト",
        base_stats=StatSet(hp=base_hp, attack=100, defense=base_def,
                           sp_attack=100, sp_defense=100, speed=100),
        types=["normal"],
    )


svc = SurvivalService(StatCalculator())

# Engineered test case (verified by hand):
# base_hp=100, base_def=100, neutral
# power=120, atk=500, physical, type_mult=1.0
# damage = int(22*120*500/def_final/50 + 2) = int(26400/def_final + 2)
# Minimum total SP = 33
# prefer_hp: sp_hp=2, sp_def=31  (HP=177, def=151, damage=176 < 177)
# prefer_def: sp_hp=1, sp_def=32  (HP=176, def=152, damage=175 < 176)
STRONG_ATTACK = AttackInput(power=120, attacker_atk=500, is_physical=True, type_multiplier=1.0)


class TestSurvivalService:
    def test_no_sp_needed_returns_zeros(self):
        # Weak attack: damage will always be less than HP
        weak_attack = AttackInput(power=40, attacker_atk=100, is_physical=True, type_multiplier=1.0)
        mon = make_pokemon(100, 100)
        prefer_hp, prefer_def = svc.optimize(mon, weak_attack)
        assert prefer_hp.total_sp == 0
        assert prefer_def.total_sp == 0
        assert prefer_hp.survived is True

    def test_minimum_total_sp_is_correct(self):
        mon = make_pokemon(100, 100)
        prefer_hp, prefer_def = svc.optimize(mon, STRONG_ATTACK)
        assert prefer_hp.total_sp == 33
        assert prefer_def.total_sp == 33

    def test_prefer_hp_has_higher_sp_hp(self):
        mon = make_pokemon(100, 100)
        prefer_hp, prefer_def = svc.optimize(mon, STRONG_ATTACK)
        assert prefer_hp.sp_hp >= prefer_def.sp_hp

    def test_prefer_def_has_higher_sp_def(self):
        mon = make_pokemon(100, 100)
        prefer_hp, prefer_def = svc.optimize(mon, STRONG_ATTACK)
        assert prefer_def.sp_def >= prefer_hp.sp_def

    def test_prefer_hp_exact_values(self):
        mon = make_pokemon(100, 100)
        prefer_hp, _ = svc.optimize(mon, STRONG_ATTACK)
        assert prefer_hp.sp_hp == 2
        assert prefer_hp.sp_def == 31
        assert prefer_hp.final_hp == 177

    def test_prefer_def_exact_values(self):
        mon = make_pokemon(100, 100)
        _, prefer_def = svc.optimize(mon, STRONG_ATTACK)
        assert prefer_def.sp_hp == 1
        assert prefer_def.sp_def == 32
        assert prefer_def.final_hp == 176

    def test_both_results_actually_survive(self):
        mon = make_pokemon(100, 100)
        prefer_hp, prefer_def = svc.optimize(mon, STRONG_ATTACK)
        assert prefer_hp.survived is True
        assert prefer_def.survived is True

    def test_special_attack_uses_sp_defense_base(self):
        # Pokemon with base_def=100 but base_sp_def=50
        # Special attack: power=120, atk=300, type_mult=1.0
        # damage = int(22*120*300/sp_def_final/50 + 2) = int(15840/sp_def_final + 2)
        # At sp_def=0: sp_def_final = int((50+20)*1.0) = 70, damage = int(15840/70+2) = int(228.28) = 228 > 175 (HP at sp_hp=0)
        # This test verifies that sp_defense base stat is used, not defense
        from domain.models.stats import StatSet
        from domain.models.pokemon import Pokemon as Poke
        mon = Poke(
            id=2, name_en="SpecTest", name_zh="測試", name_ja="テスト",
            base_stats=StatSet(hp=100, attack=100, defense=100, sp_attack=100, sp_defense=50, speed=100),
            types=["normal"],
        )
        special_attack = AttackInput(power=120, attacker_atk=300, is_physical=False, type_multiplier=1.0)
        prefer_hp, prefer_def = svc.optimize(mon, special_attack)
        # Both should survive
        assert prefer_hp.survived is True
        assert prefer_def.survived is True
        # final_def should reflect sp_defense (base 50), not defense (base 100)
        # sp_defense_final at sp_def=0: int((50+20+0)*1.0) = 70
        # sp_defense_final at sp_def>0: int((50+20+sp_def)*1.0)
        # Verify final_def is based on sp_defense (50), not defense (100)
        # If bug existed, final_def would be ~120+ instead of ~70+
        assert prefer_hp.final_def < 100  # Must be sp_defense-based, not defense-based
