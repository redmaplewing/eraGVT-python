"""S33 背景色：expected 由 PRINT_RGBTEXT 原文及 Emuera 推導。"""

import pytest

from test_narration_s30 import ctx, data, svc


@pytest.mark.parametrize("background,name,expected", [
    ("#000000", "黒", "#ffffff"),
    ("#ffffff", "純白", "#000000"),
    ("#0a0a00", "黒", "#000000"),
])
def test_background_contrast(ctx, background, name, expected):
    """汎用関数/PRINT_RGBTEXT（色名、文字列）.ERB@PRINT_RGBTEXT:102–125。

    GETBGCOLOR：reference/emuera-1824/Emuera/GameData/Function/Creator.Method.cs:584–599。
    """
    ctx.out.set_bgcolor(background)
    assert ctx.narration.run_function(ctx, "PRINT_RGBTEXT", args=[name, "sample"])
    ctx.out.printl()
    assert ctx.out.lines[-1].parts[0].segments[0].color == expected
    assert ctx.out.bgcolor == background
    ctx.out.reset_bgcolor()
    assert ctx.out.bgcolor == "#000000"


def test_color_t_shape_supported(svc):
    assert svc.catalog.unsupported_reason("COLOR_T_SHAPE") is None
