"""Comprehensive Unit and Integration Tests for Social Media Adapters (Telegram, LinkedIn, Facebook)."""

import pytest
from integrations.telegram_adapter import TelegramAdapter
from integrations.linkedin_adapter import LinkedInAdapter
from integrations.facebook_adapter import FacebookAdapter
from integrations.social_media import SocialMediaIntegration


@pytest.mark.asyncio
async def test_telegram_adapter_simulation_and_dispatch():
    """Verify Telegram adapter runs in safe simulation mode when API credentials are absent."""
    adapter = TelegramAdapter(bot_token="", channel_id="", group_id="")
    
    # 1. Connection status
    status = await adapter.get_connection_status()
    assert status["platform"] == "telegram"
    assert status["live"] is False
    assert status["status"] == "connected_simulation"
    assert "simulated_subscribers" in status

    # 2. Broadcast to channel
    res_channel = await adapter.broadcast_to_channel("Test announcement for Pharma Gebeya network")
    assert res_channel["success"] is True
    assert res_channel["mode"] == "simulated"
    assert "sim_tg_chan_" in res_channel["message_id"]

    # 3. Send group message
    res_group = await adapter.send_group_message("Community discussion on cold-chain medicine storage")
    assert res_group["success"] is True
    assert res_group["mode"] == "simulated"
    assert "sim_tg_grp_" in res_group["message_id"]

    # 4. Recent group messages polling
    messages = await adapter.fetch_group_recent_messages(limit=5)
    assert isinstance(messages, list)
    assert len(messages) >= 1
    assert "text" in messages[0]
    assert "from_user" in messages[0]

    # 5. Group sentiment analysis
    sent = await adapter.analyze_group_sentiment()
    assert "dominant_community_topic" in sent
    assert "sample_questions" in sent
    assert len(sent["sample_questions"]) >= 1


@pytest.mark.asyncio
async def test_linkedin_adapter_simulation_and_analytics():
    """Verify LinkedIn adapter handles professional posts and analytics in simulation mode."""
    adapter = LinkedInAdapter(access_token="", author_urn="")

    # 1. Connection status
    status = await adapter.get_connection_status()
    assert status["platform"] == "linkedin"
    assert status["live"] is False
    assert status["status"] == "connected_simulation"

    # 2. Publish share
    res_share = await adapter.publish_share(
        text="Strategic overview: Digitizing pharmaceutical supply chains in East Africa.",
        title="Pharma Gebeya Supply Chain Whitepaper"
    )
    assert res_share["success"] is True
    assert res_share["mode"] == "simulated"
    assert res_share["platform"] == "linkedin"
    assert "urn:li:share:" in res_share["post_urn"]

    # 3. Post analytics
    analytics = await adapter.get_post_analytics(res_share["post_urn"])
    assert analytics["platform"] == "linkedin"
    assert "impressions" in analytics
    assert "reactions" in analytics
    assert "comments" in analytics
    assert analytics["impressions"] >= 0


@pytest.mark.asyncio
async def test_facebook_adapter_simulation_and_insights():
    """Verify Facebook adapter handles Page updates and Meta Graph insights in simulation mode."""
    adapter = FacebookAdapter(access_token="", page_id="")

    # 1. Connection status
    status = await adapter.get_connection_status()
    assert status["platform"] == "facebook"
    assert status["live"] is False
    assert status["status"] == "connected_simulation"

    # 2. Publish page post
    res_post = await adapter.publish_page_post(
        message="Important announcement: Verified supplier registration is now open on Pharma Gebeya."
    )
    assert res_post["success"] is True
    assert res_post["mode"] == "simulated"
    assert res_post["platform"] == "facebook"
    assert "sim_fb_post_" in res_post["post_id"]

    # 3. Page insights
    insights = await adapter.get_page_insights()
    assert insights["platform"] == "facebook"
    assert "page_impressions" in insights
    assert "page_engaged_users" in insights
    assert insights["page_impressions"] >= 0


@pytest.mark.asyncio
async def test_social_media_manager_multi_channel():
    """Verify SocialMediaIntegration orchestrates all platform adapters unifiedly."""
    manager = SocialMediaIntegration()

    # 1. Unified status across all platforms
    all_status = await manager.get_all_platforms_status()
    assert "telegram" in all_status
    assert "linkedin" in all_status
    assert "facebook" in all_status
    assert all_status["telegram"]["platform"] == "telegram"
    assert all_status["linkedin"]["platform"] == "linkedin"
    assert all_status["facebook"]["platform"] == "facebook"

    # 2. Dispatch to Telegram Channel via stage -> publish
    post_tg = await manager.stage_post_async(
        platform="telegram",
        content="Multi-channel test post to Telegram"
    )
    tg_res = await manager.publish_post(post_id=post_tg["id"], approved_by="director")
    assert tg_res["success"] is True
    assert tg_res["dispatch"]["mode"] == "simulated"

    # 3. Dispatch to LinkedIn
    post_li = await manager.stage_post_async(
        platform="linkedin",
        content="Multi-channel test post to LinkedIn"
    )
    li_res = await manager.publish_post(post_id=post_li["id"], approved_by="director")
    assert li_res["success"] is True
    assert li_res["dispatch"]["mode"] == "simulated"

    # 4. Dispatch to Facebook
    post_fb = await manager.stage_post_async(
        platform="facebook",
        content="Multi-channel test post to Facebook"
    )
    fb_res = await manager.publish_post(post_id=post_fb["id"], approved_by="director")
    assert fb_res["success"] is True
    assert fb_res["dispatch"]["mode"] == "simulated"
