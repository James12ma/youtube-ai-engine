"""Manim Community 15s statistical explainer — vertical 1080x1920 @ 30fps.
MIT license. Offline only.
"""
from manim import *

config.pixel_width = 1080
config.pixel_height = 1920
config.frame_rate = 30
config.background_color = "#FAF9F6"
config.frame_width = 9
config.frame_height = 16


class InternetStatsExplainer(Scene):
    def construct(self):
        title = Text(
            "WHAT IF THE INTERNET\nVANISHED FOR 24H?",
            font_size=36,
            color="#151515",
            weight=BOLD,
            line_spacing=1.05,
        ).move_to(UP * 5.5)

        line = Line(LEFT * 3.5, RIGHT * 3.5, color="#E63336", stroke_width=6).next_to(title, DOWN, buff=0.35)

        self.play(FadeIn(title, shift=UP * 0.25), Create(line), run_time=1.1)
        self.wait(0.3)

        labels = ["Payments", "Messaging", "Logistics", "Local radio"]
        values = [0.92, 0.88, 0.75, 0.12]
        colors = ["#E63336", "#E63336", "#C62828", "#2E7D32"]
        bars = VGroup()
        texts = VGroup()
        pct_group = VGroup()
        base_y = -1.5
        for i, (lab, val, col) in enumerate(zip(labels, values, colors)):
            x = -3.0 + i * 2.0
            bar = Rectangle(
                width=1.3,
                height=0.05,
                fill_color=col,
                fill_opacity=0.95,
                stroke_width=0,
            ).move_to([x, base_y, 0])
            bar.align_to([0, base_y, 0], DOWN)
            bars.add(bar)
            t = Text(lab, font_size=18, color="#151515").next_to(bar, DOWN, buff=0.3)
            texts.add(t)

        self.play(LaggedStart(*[FadeIn(t) for t in texts], lag_ratio=0.15), run_time=0.8)
        grow = []
        for bar, val in zip(bars, values):
            new_bar = Rectangle(
                width=1.3,
                height=5.5 * val,
                fill_color=bar.get_fill_color(),
                fill_opacity=0.95,
                stroke_width=0,
            )
            new_bar.move_to(bar.get_center())
            new_bar.align_to(bar, DOWN)
            grow.append(Transform(bar, new_bar))
        self.play(*grow, run_time=2.0)
        self.wait(0.3)

        for bar, val in zip(bars, values):
            pct = Text(f"{int(val*100)}%", font_size=24, color="#151515", weight=BOLD)
            pct.next_to(bar, UP, buff=0.2)
            pct_group.add(pct)
        self.play(FadeIn(pct_group, shift=UP * 0.15), run_time=0.7)
        self.wait(0.6)

        takeaway = Text(
            "Digital systems stall.\nOffline channels hold.",
            font_size=28,
            color="#151515",
            line_spacing=1.1,
        ).move_to(DOWN * 5.8)
        self.play(FadeIn(takeaway), run_time=0.9)
        self.wait(1.2)

        footer = Text("HYPOTHETICAL  •  NOT REAL NEWS", font_size=18, color="#666666")
        footer.move_to(DOWN * 7.2)
        self.play(FadeIn(footer), run_time=0.4)
        self.wait(1.0)
