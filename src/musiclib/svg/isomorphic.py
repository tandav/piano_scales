"""
https://notes.tandav.me/notes/3548
"""
import abc
import cmath
import math
import uuid
import svg
from colortool import Color

from musiclib import config
from musiclib.interval import AbstractInterval
import numpy as np


class IsomorphicKeyboard(abc.ABC):
    def __init__(
        self,
        interval_colors: dict[AbstractInterval | int, Color] | None = None,
        interval_parts_colors: dict[int, dict[int, Color]] | None = None,
        interval_text: dict[AbstractInterval | int, str] | str | None = 'abstract_interval',
        interval_strokes: dict[AbstractInterval | int, Color] | None = None,
        n_rows: int | None = 7,
        n_cols: int = 13,
        radius: int = 30,
        font_size_radius_ratio: float = 0.5,
        round_points: bool = True,
    ) -> None:
        self.n_rows = n_rows
        self.n_cols = n_cols
        self.radius = radius
        self.elements: list[svg.Element] = []
        self.interval_colors = interval_colors or {}
        self.interval_parts_colors = interval_parts_colors or {}
        self.interval_text = interval_text
        self.font_size = int(radius * font_size_radius_ratio)
        self.round_points = round_points
        self.interval_strokes = interval_strokes or {}
        self.defs = svg.Defs(elements=[])
        self.elements.append(self.defs)
        self.id_suffix = str(uuid.uuid4()).split('-')[0]

        if n_rows is None:
            for col in range(-2, n_cols + 1):
                self.add_key(0, col)
            return
        
        for row in range(-1, n_rows + 1):
            for col in range(-2, n_cols + 1, 2):
                self.add_key(row, col + row % 2)

    @abc.abstractmethod
    def col_to_x(self, col: float) -> float:
        ...

    @abc.abstractmethod
    def row_to_y(self, row: float) -> float:
        ...

    @property
    @abc.abstractmethod
    def width(self) -> int:
        ...

    @property
    @abc.abstractmethod
    def height(self) -> int:
        ...

    def add_key(self, row: float, col: float) -> None:
        interval = round(col)
        x = self.col_to_x(col)
        y = self.row_to_y(row)
        color = self.interval_colors.get(interval, self.interval_colors.get(AbstractInterval(interval), config.BLACK_PALE))
        points = self.key_points(x, y, self.radius)
        if self.round_points:
            points = [round(p, 1) for p in points]

        polygon_kw = dict(
            class_=['polygon-colored'],
            fill=color.css_hex,
            points=points,
            # clip_path='url(#key-clip)',
        )
        id_ = f'row-{row}-col-{col}-{self.id_suffix}'
        self.defs.elements.append(svg.ClipPath(id=id_, elements=[svg.Polygon(**polygon_kw)]))
        stroke = self.interval_strokes.get(interval, self.interval_strokes.get(AbstractInterval(interval), None))
        if stroke is not None:
            polygon_kw['stroke'] = stroke['stroke'].css_hex
            polygon_kw['stroke_width'] = stroke.get('stroke_width', 1) * 2
            polygon_kw['clip_path'] = f'url(#{id_})'
        self.elements.append(svg.Polygon(**polygon_kw))

#       self.texts.append(svg.Text(x=x, y=y, text=f'{x:.1f}{y:.1f}', font_size=10, text_anchor='middle', dominant_baseline='middle'))
#       self.texts.append(svg.Text(x=x, y=y, text=f'{row}, {col}', font_size=10, text_anchor='middle', dominant_baseline='middle'))

        if self.interval_text is None:
            text = None
        elif isinstance(self.interval_text, dict):
            text = self.interval_text.get(interval, self.interval_text.get(AbstractInterval(interval), None))
        elif isinstance(self.interval_text, str):
            if self.interval_text == 'interval':
                text = np.base_repr(interval, base=12)
            elif self.interval_text == 'abstract_interval':
                text = str(AbstractInterval(interval))
            else:
                raise NotImplementedError(f'invalid self.interval_text={self.interval_text}, can be None, dict or "interval" or "abstract_interval"')
        else:
            raise NotImplementedError(f'invalid self.interval_text={self.interval_text}')

        if text is not None:
            self.elements.append(svg.Text(
                x=x,
                y=y,
                text=text,
                font_size=self.font_size,
                font_family='monospace',
                text_anchor='middle',
                dominant_baseline='middle',
                pointer_events='none',  # probably not needed when using event.preventDefault() on transparent polygon
                # onclick=f"play_note('{note}')",
                # onmousedown=f"midi_message('note_on', '{note}')",
                # onmouseup=f"midi_message('note_off', '{note}')",
            ))

        # transparent polygon on top for mouse events
        # polygon = svg.Polygon(
        #     class_=['polygon-transparent'],
        #     points=points,
        #     fill=Color.from_rgba_int((0, 0, 0, 0)).css_rgba,
        #     # stroke='black',
        #     # stroke_width=1,
        #     # onmousedown=f"midi_message('note_on', '{note}')",
        #     # onmouseup=f"midi_message('note_off', '{note}')",
        # )
        # self.elements.append(polygon)

        for part, color in self.interval_parts_colors.get(interval, {}).items():
            self.elements.append(
                svg.Polygon(
                    points=self.key_part_points(x, y, part),
                    fill=Color.random().css_hex,
                ),
            )


    @abc.abstractmethod
    def key_points(self, x: float, y: float) -> list[float]:
        ...

    @abc.abstractmethod
    def key_part_points(self, x: float, y: float, part: int) -> list[float]:
        ...

    @property
    def svg(self) -> svg.SVG:
        return svg.SVG(
            width=self.width,
            height=self.height,
            elements=self.elements,
        )

    def _repr_svg_(self) -> str:
        return str(self.svg)


class Square(IsomorphicKeyboard):
    def col_to_x(self, col: float) -> float:
        return self.radius * (col + 1)

    def row_to_y(self, row: float) -> float:
        return self.radius * (row + 1)

    @property
    def width(self) -> int:
        return int(self.col_to_x(self.n_cols))

    @property
    def height(self) -> int:
        return int(self.row_to_y(self.n_rows))
    
    @property
    def h(self):
        return 2 ** 0.5 / 2 * self.radius

    @staticmethod
    def vertex(x: float, y: float, radius: float, i: int, phase: float = 0) -> tuple[float, float]:
        phase_start = 2 * math.pi / 2
        theta = phase_start + phase + 2 * math.pi * i / 4
        p = complex(y, x) + radius * cmath.exp(1j * theta)
        return p.imag, p.real

    def key_points(self, x: float, y: float, radius: float) -> list[float]:
        points = []
        for i in range(4):
            points += self.vertex(x, y, radius, i)
        return points
    
    def key_part_points(self, x: float, y: float, part: int) -> list[float]:
        i = part // 2
        return [
            x, 
            y, 
            *self.vertex(x, y, self.h, i, phase=2 * math.pi / 8), # todo: support 12 parts
            *self.vertex(x, y, self.radius, i + part % 2),
        ]


class Hex(IsomorphicKeyboard):
    def col_to_x(self, col: float) -> float:
        return self.h * (col + 1)

    def row_to_y(self, row: float) -> float:
        return self.radius * (row * 1.5 + 1)

    @property
    def width(self) -> int:
        return int(self.col_to_x(self.n_cols))

    @property
    def height(self) -> int:
        return int(self.row_to_y(self.n_rows) - 0.5 * self.radius)
    
    @property
    def h(self):
        return 3 ** 0.5 / 2 * self.radius

    @staticmethod
    def vertex(x: float, y: float, radius: float, i: int, phase: float = 0) -> tuple[float, float]:
        phase_start = 2 * math.pi / 2
        theta = phase_start + phase + 2 * math.pi * i / 6
        p = complex(y, x) + radius * cmath.exp(1j * theta)
        return p.imag, p.real

    def key_points(self, x: float, y: float, radius: float) -> list[float]:
        points = []
        for i in range(7):
            points += self.vertex(x, y, radius, i)
        return points
    
    def key_part_points(self, x: float, y: float, part: int) -> list[float]:
        i = part // 2
        return [
            x, 
            y, 
            *self.vertex(x, y, self.h, i, phase=2 * math.pi / 12),
            *self.vertex(x, y, self.radius, i + part % 2),
        ]


class IsoPiano(IsomorphicKeyboard):
    def __init__(
        self,
        n_rows: int | None = None,
        key_height: int = 100,
        offset_x: int = 0,
        extra_radius_width_on_right: bool = False,
        **kwargs,
    ) -> None:
        if n_rows is not None:
            raise NotImplementedError('n_rows is not supported for Piano')
        self.key_height = key_height
        self.offset_x = offset_x
        self.extra_radius_width_on_right = extra_radius_width_on_right
        super().__init__(
            n_rows=n_rows,
            **kwargs,
        )

    def col_to_x(self, col: float) -> float:
        return self.radius * (col * 2 + 1) + self.offset_x

    def row_to_y(self, row: float) -> float:
        return self.key_height // 2

    @property
    def width(self) -> int:
        if self.extra_radius_width_on_right:
            return int(self.col_to_x(self.n_cols))
        return int(self.col_to_x(self.n_cols - 0.5))

    @property
    def height(self) -> int:
        return self.key_height
    
    def key_part_points(self, x: float, y: float, part: int) -> list[float]:
        raise NotImplementedError('TODO: split vertically')

    @staticmethod
    def vertex(x: float, y: float, radius_w: float, i: int, radius_h: float) -> tuple[float, float]:
        if i % 4 == 0:
            return x - radius_w, y - radius_h
        if i == 1:
            return x + radius_w, y - radius_h
        if i == 2:
            return x + radius_w, y + radius_h
        if i == 3:
            return x - radius_w, y + radius_h
        raise ValueError(f'invalid i={i}')

    def key_points(self, x: float, y: float, radius: float) -> list[float]:
        points = []
        for i in range(5):
            points += self.vertex(x, y, radius, i, self.key_height / 2)
        return points