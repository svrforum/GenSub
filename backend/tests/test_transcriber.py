from app.services.transcriber import segments_from_whisper_output


class _FakeWord:
    def __init__(self, start, end, word):
        self.start = start
        self.end = end
        self.word = word


class _FakeSegment:
    def __init__(self, start, end, text, avg_logprob, no_speech_prob, words=None):
        self.start = start
        self.end = end
        self.text = text
        self.avg_logprob = avg_logprob
        self.no_speech_prob = no_speech_prob
        self.words = words


def test_segments_from_whisper_output_maps_fields():
    whisper_segs = [
        _FakeSegment(
            0.0, 2.5, " hi there ", -0.3, 0.01,
            [_FakeWord(0, 1, "hi"), _FakeWord(1, 2, "there")],
        ),
        _FakeSegment(2.5, 4.0, " bye ", -0.4, 0.02, None),
    ]
    result = segments_from_whisper_output(whisper_segs)
    assert len(result) == 2
    assert result[0].idx == 0
    assert result[0].text == "hi there"
    assert result[0].avg_logprob == -0.3
    assert result[1].text == "bye"
    assert result[1].idx == 1
