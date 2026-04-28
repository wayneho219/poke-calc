from domain.models.nature import NatureRegistry
from domain.models.stats import StatSet
from domain.models.pokemon import Pokemon
from application.calculator import StatCalculator
from application.speed_service import SpeedService

NEUTRAL = NatureRegistry.get_by_name("Hardy")

def make_pokemon(pid: int, base_speed: int) -> Pokemon:
    return Pokemon(
        id=pid, name_en=f"Mon{pid}", name_zh="測試", name_ja="テスト",
        base_stats=StatSet(hp=100, attack=100, defense=100, sp_attack=100, sp_defense=100, speed=base_speed),
        types=["normal"],
    )


svc = SpeedService(StatCalculator())


class TestSpeedService:
    def test_no_sp_needed_already_faster(self):
        # user base 100, target base 80 (both neutral)
        # user speed = 120, target speed = 100
        user   = make_pokemon(1, 100)
        target = make_pokemon(2, 80)
        result = svc.min_sp_to_outspeed(user, target)
        assert result.sp_needed == 0
        assert result.my_speed > result.target_speed

    def test_sp_needed_to_outspeed(self):
        # user base 80 → neutral speed = 100+sp
        # target base 100 → neutral speed = 120
        # Need 100+sp > 120 → sp >= 21
        user   = make_pokemon(1, 80)
        target = make_pokemon(2, 100)
        result = svc.min_sp_to_outspeed(user, target)
        assert result.sp_needed == 21
        assert result.my_speed == 121
        assert result.target_speed == 120

    def test_cannot_outspeed_returns_none(self):
        # user base 60, max speed = 112; target base 100, speed = 120
        user   = make_pokemon(1, 60)
        target = make_pokemon(2, 100)
        result = svc.min_sp_to_outspeed(user, target)
        assert result is None

    def test_equal_base_speed_same_nature(self):
        # Both base 100 neutral: user needs sp=1 to outspeed
        user   = make_pokemon(1, 100)
        target = make_pokemon(2, 100)
        result = svc.min_sp_to_outspeed(user, target)
        assert result.sp_needed == 1
        assert result.my_speed == 121

    def test_nature_aware_timid_vs_brave(self):
        from domain.models.nature import NatureRegistry
        import dataclasses
        # Timid user (×1.1 speed), base 80: speed = int((80+20+0)*1.1) = 110
        # Brave target (×0.9 speed), base 100: speed = int((100+20+0)*0.9) = 108
        # user already faster at sp=0
        timid = NatureRegistry.get_by_name("Timid")
        brave = NatureRegistry.get_by_name("Brave")
        user   = dataclasses.replace(make_pokemon(1, 80),  nature=timid)
        target = dataclasses.replace(make_pokemon(2, 100), nature=brave)
        result = svc.min_sp_to_outspeed(user, target)
        assert result is not None
        assert result.sp_needed == 0
        assert result.my_speed == 110
        assert result.target_speed == 108


class TestSpeedServiceTargetSP:
    def test_target_sp_raises_target_speed(self):
        # target base 80, sp=4: speed = int((80+20+4)*1.0) = 104
        # user base 100, sp=0: speed = 120 > 104, no SP needed
        user   = make_pokemon(1, 100)
        target = make_pokemon(2, 80)
        result = svc.min_sp_to_outspeed(user, target, target_sp=4)
        assert result is not None
        assert result.sp_needed == 0
        assert result.target_speed == 104

    def test_target_sp_forces_user_to_invest(self):
        # user base 80 sp=0: speed = int((80+20)*1.0) = 100
        # target base 80 sp=4: speed = int((80+20+4)*1.0) = 104
        # need 100+sp > 104 → sp=5, my_speed=105
        user   = make_pokemon(1, 80)
        target = make_pokemon(2, 80)
        result = svc.min_sp_to_outspeed(user, target, target_sp=4)
        assert result is not None
        assert result.sp_needed == 5
        assert result.my_speed == 105
        assert result.target_speed == 104

    def test_target_sp_max_still_cannot_outspeed(self):
        # user base 60 max speed = int((60+20+32)*1.0) = 112
        # target base 100 sp=32 speed = int((100+20+32)*1.0) = 152 → None
        user   = make_pokemon(1, 60)
        target = make_pokemon(2, 100)
        result = svc.min_sp_to_outspeed(user, target, target_sp=32)
        assert result is None


class TestSpeedMultipliers:
    def test_default_mult_unchanged(self):
        # Default (mult=1.0) must match the original behaviour exactly.
        user   = make_pokemon(1, 80)
        target = make_pokemon(2, 100)
        assert svc.min_sp_to_outspeed(user, target) == \
               svc.min_sp_to_outspeed(user, target, my_mult=1.0, tgt_mult=1.0)

    def test_my_scarf_reduces_sp_needed(self):
        # Without scarf: user base 80 needs sp=21 to beat target base 100 (speed=120).
        # With scarf (×1.5): user speed at sp=0 = floor(100 * 1.5) = 150 > 120 → sp=0.
        user   = make_pokemon(1, 80)
        target = make_pokemon(2, 100)
        result = svc.min_sp_to_outspeed(user, target, my_mult=1.5)
        assert result is not None
        assert result.sp_needed == 0
        assert result.my_speed == 150
        assert result.target_speed == 120

    def test_target_scarf_requires_more_sp(self):
        # user base 100 (speed=120 at sp=0), target base 80 (speed=100).
        # Target with scarf: tgt_speed = floor(100 * 1.5) = 150.
        # Need user speed > 150: floor((100+20+sp)*1.0) > 150 → 120+sp > 150 → sp=31 gives 151.
        user   = make_pokemon(1, 100)
        target = make_pokemon(2, 80)
        result = svc.min_sp_to_outspeed(user, target, tgt_mult=1.5)
        assert result is not None
        assert result.sp_needed == 31
        assert result.my_speed == 151
        assert result.target_speed == 150

    def test_target_paralysis_reduces_sp_needed(self):
        # user base 80 (speed=100 at sp=0), target base 100.
        # Target paralysed (×0.5): tgt_speed = floor(120 * 0.5) = 60.
        # user sp=0: speed=100 > 60 → sp=0.
        user   = make_pokemon(1, 80)
        target = make_pokemon(2, 100)
        result = svc.min_sp_to_outspeed(user, target, tgt_mult=0.5)
        assert result is not None
        assert result.sp_needed == 0
        assert result.my_speed == 100
        assert result.target_speed == 60

    def test_my_paralysis_increases_sp_needed(self):
        # user base 100, target base 80 (speed=100).
        # user paralysed (×0.5): my_speed at sp=0 = floor(120 * 0.5) = 60 < 100.
        # Need floor((120+sp)*0.5) > 100 → (120+sp)*0.5 > 100 → 120+sp > 200 → sp > 80
        # But sp max is 32: floor((120+32)*0.5) = floor(76) = 76 < 100 → None.
        user   = make_pokemon(1, 100)
        target = make_pokemon(2, 80)
        result = svc.min_sp_to_outspeed(user, target, my_mult=0.5)
        assert result is None

    def test_both_multipliers_apply_independently(self):
        # Both sides with Tailwind (×2.0): target base 80 tgt_speed=200, user base 80.
        # floor((80+20+sp)*1.0 * 2.0) > 200 → floor((100+sp)*2.0) > 200
        # sp=0: floor(100*2.0)=200, not > 200. sp=1: floor(101*2.0)=202 > 200. → sp=1.
        user   = make_pokemon(1, 80)
        target = make_pokemon(2, 80)
        result = svc.min_sp_to_outspeed(user, target, my_mult=2.0, tgt_mult=2.0)
        assert result is not None
        assert result.sp_needed == 1
        assert result.my_speed == 202
        assert result.target_speed == 200
