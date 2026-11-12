def format_telegram_payload(channel_or_group: str, text: str, parse_mode: str = 'HTML') -> dict:
    return {
        'target': channel_or_group,
        'text': text.strip(),
        'parse_mode': parse_mode,
        'status': 'ready_to_dispatch'
    }
