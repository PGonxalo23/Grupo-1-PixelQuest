"""Secuencia narrativa de flujo.docx, independiente de Pygame."""


class OpeningCinematic:
    MESSAGES = ("Ellos te lo arrebataron…", "Encuéntralos y destrúyelos…", "Venga a tu familia…")
    FADE_IN, HOLD, FADE_OUT, GAP = 1.5, 2.0, 1.3, 0.45
    MESSAGE_DURATION = FADE_IN + HOLD + FADE_OUT + GAP
    DURATION = len(MESSAGES) * MESSAGE_DURATION

    def __init__(self):
        self.elapsed = 0.0

    @property
    def finished(self):
        return self.elapsed >= self.DURATION

    @property
    def message(self):
        index = min(len(self.MESSAGES) - 1, int(self.elapsed / self.MESSAGE_DURATION))
        return self.MESSAGES[index]

    @property
    def alpha(self):
        if self.finished:
            return 0
        phase = self.elapsed % self.MESSAGE_DURATION
        if phase < self.FADE_IN:
            return round(255 * phase / self.FADE_IN)
        if phase < self.FADE_IN + self.HOLD:
            return 255
        if phase < self.FADE_IN + self.HOLD + self.FADE_OUT:
            return round(255 * (1 - (phase - self.FADE_IN - self.HOLD) / self.FADE_OUT))
        return 0

    def update(self, dt):
        self.elapsed = min(self.DURATION, self.elapsed + max(0, dt))

    def skip(self):
        self.elapsed = self.DURATION
