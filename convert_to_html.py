import pandas as pd
import re

# Markdown conversion function
def basic_markdown_to_html(text):
    text = re.sub(r'```([a-z]*)\n(.*?)```', r'<pre><code class="\1">\2</code></pre>', text, flags=re.DOTALL)
    text = re.sub(r'`([^`]*)`', r'<code>\1</code>', text)
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
    text = text.replace('\n', '<br>')
    return text

# Main conversion function
def xlsx_to_html(input_xlsx, output_html):
    df = pd.read_excel(input_xlsx)

    # Update roles
    df['role'] = df['role'].replace({'user': 'Designer', 'assistant': 'Programmer'})

    # Remove the first row and keep up to 209 rows
    df = df.iloc[1:]

    # Separate Designer and Programmer contents
    designer_content = df[df['role'] == 'Designer']['content'].reset_index(drop=True)
    programmer_content = df[df['role'] == 'Programmer']['content'].reset_index(drop=True)

    max_len = max(len(designer_content), len(programmer_content))
    designer_content = designer_content.reindex(range(max_len), fill_value='')
    programmer_content = programmer_content.reindex(range(max_len), fill_value='')

    # Convert Markdown to HTML
    designer_html = designer_content.apply(basic_markdown_to_html)
    programmer_html = programmer_content.apply(basic_markdown_to_html)

    # HTML content
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Designer and Programmer Conversation</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 0; padding: 0; }}
            table {{ width: 100%; border-collapse: collapse; table-layout: fixed; }}
            th, td {{ border: 1px solid #ddd; padding: 12px; vertical-align: top; width: 50%; word-wrap: break-word; }}
            th {{ background-color: #f4f4f4; }}
            .programmer {{ background-color: #f0f0f0; }}
            pre {{ background-color: #eaeaea; padding: 10px; overflow-x: auto; }}
            code {{ font-family: monospace; background-color: #ddd; padding: 2px 4px; }}
        </style>
    </head>
    <body>
        <table>
            <tr>
                <th>Designer</th>
                <th>Programmer</th>
            </tr>
    """

    # Populate HTML table
    for d_html, p_html in zip(designer_html, programmer_html):
        html_content += f"""
            <tr>
                <td>{d_html}</td>
                <td class="programmer">{p_html}</td>
            </tr>
        """

    html_content += """
        </table>
    </body>
    </html>
    """

    with open(output_html, 'w', encoding='utf-8') as file:
        file.write(html_content)

# Example usage
xlsx_to_html('./results/programmer_compiler_conversation_deepseek14b_oss20b.xlsx', './results/c_deepseek14b_oss20b.html')