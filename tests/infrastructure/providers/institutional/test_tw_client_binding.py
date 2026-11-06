"""客户端替换只在装配时生效，不污染下一次真实装配。"""

from unittest.mock import Mock, patch

from data_provider.institutional import tw_client, tw_source


def test_source_factory_re_resolves_canonical_class_after_mock_scope():
    original = tw_client.TwInstitutionalFetcher
    fake = Mock()
    with patch.object(tw_client, "TwInstitutionalFetcher", fake):
        assert tw_source.TwInstitutionalSource().fetcher is fake.return_value
    assert type(tw_source.TwInstitutionalSource().fetcher) is original


def test_legacy_source_factory_patch_is_scoped_and_restored():
    original = tw_client.TwInstitutionalFetcher
    with patch.object(
        tw_source, "TwInstitutionalFetcher", side_effect=RuntimeError("init")
    ):
        try:
            tw_source.TwInstitutionalSource()
        except RuntimeError as exc:
            assert str(exc) == "init"
        else:
            raise AssertionError("legacy factory patch was ignored")
    assert type(tw_source.TwInstitutionalSource().fetcher) is original
