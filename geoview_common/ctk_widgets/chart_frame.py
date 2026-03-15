"""
GeoView Chart Frame
===================
Matplotlib chart embedded in CustomTkinter with GeoView styling.
Supports automatic dark/light mode switching.
"""

try:
    import customtkinter as ctk
    HAS_CTK = True
except ImportError:
    HAS_CTK = False

try:
    import matplotlib
    matplotlib.use("TkAgg")
    # Pretendard 폰트 글로벌 설정 (한글 지원)
    matplotlib.rcParams['font.family'] = 'Pretendard'
    matplotlib.rcParams['axes.unicode_minus'] = False  # 마이너스 기호 깨짐 방지
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    HAS_MPL = True
except ImportError:
    HAS_MPL = False

from ..styles import colors


def _is_dark():
    """Check if current CTk appearance mode is dark."""
    try:
        return ctk.get_appearance_mode().lower() == "dark"
    except Exception:
        return True


def _chart_colors():
    """Return (bg, text, grid, spine) colors for current theme."""
    if _is_dark():
        return (colors.DARK_SURFACE, colors.DARK_TEXT,
                colors.DARK_BORDER, colors.DARK_BORDER)
    return (colors.CHART_BG, colors.TEXT_PRIMARY,
            colors.TABLE_BORDER, colors.TABLE_BORDER)


class ChartFrame:
    """
    Embeddable matplotlib chart with GeoView styling.
    Auto-detects dark/light mode.

    Usage:
        chart = ChartFrame(parent, title="My Chart")
        ax = chart.ax
        ax.plot(x, y, color=chart.palette[0])
        chart.refresh()
    """

    def __init__(self, parent, title: str = "",
                 figsize: tuple = (5, 3.5), dpi: int = 100,
                 nrows: int = 1, ncols: int = 1):
        if not HAS_CTK or not HAS_MPL:
            raise ImportError("customtkinter and matplotlib required")

        self.frame = ctk.CTkFrame(parent)
        self.palette = colors.CHART_PALETTE
        self.title = title

        bg, text, grid, spine = _chart_colors()

        self.fig = Figure(figsize=figsize, dpi=dpi, facecolor=bg)

        if nrows == 1 and ncols == 1:
            self.ax = self.fig.add_subplot(111)
            self.axes = [self.ax]
        else:
            self.axes = []
            for i in range(nrows * ncols):
                ax = self.fig.add_subplot(nrows, ncols, i + 1)
                self.axes.append(ax)
            self.ax = self.axes[0]

        for ax in self.axes:
            self._style_ax(ax, bg, text, grid, spine)

        if title and len(self.axes) == 1:
            self.ax.set_title(title, fontsize=10, fontweight="bold",
                              color=text, pad=10)

        self.canvas = FigureCanvasTkAgg(self.fig, master=self.frame)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

    def _style_ax(self, ax, bg, text, grid, spine):
        """Apply theme-aware styling to an axes."""
        ax.set_facecolor(bg)
        ax.tick_params(colors=text, labelsize=8)
        ax.xaxis.label.set_color(text)
        ax.yaxis.label.set_color(text)
        ax.title.set_color(text)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_color(spine)
        ax.spines["bottom"].set_color(spine)
        ax.grid(True, alpha=0.3, color=grid)

    def _current_style(self):
        return _chart_colors()

    def clear(self, ax=None):
        """Clear chart and re-apply styling."""
        target = ax or self.ax
        target.clear()
        bg, text, grid, spine = self._current_style()
        self._style_ax(target, bg, text, grid, spine)
        self.fig.set_facecolor(bg)
        if self.title and target is self.ax and len(self.axes) == 1:
            target.set_title(self.title, fontsize=10, fontweight="bold",
                             color=text, pad=10)

    def clear_all(self):
        """Clear all axes."""
        for ax in self.axes:
            self.clear(ax)

    def refresh(self):
        """Redraw the chart."""
        self.fig.tight_layout()
        self.canvas.draw()

    def pack(self, **kwargs):
        self.frame.pack(**kwargs)

    def grid(self, **kwargs):
        self.frame.grid(**kwargs)

    def place(self, **kwargs):
        self.frame.place(**kwargs)

    def get_figure(self):
        return self.fig

    def draw(self):
        self.refresh()

    def update_theme(self):
        """Call after theme toggle to refresh colors."""
        bg, text, grid, spine = self._current_style()
        self.fig.set_facecolor(bg)
        for ax in self.axes:
            self._style_ax(ax, bg, text, grid, spine)
        self.refresh()
