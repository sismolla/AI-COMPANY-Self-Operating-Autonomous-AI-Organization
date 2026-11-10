def format_report(title: str, sections: dict) -> str:
    lines = [f'# {title}', '', f'> Generated on automated cycle', '']
    for heading, content in sections.items():
        lines.append(f'## {heading}')
        lines.append(str(content))
        lines.append('')
    return '\n'.join(lines)
