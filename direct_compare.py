from website_provider import AmazonProvider
from options_finder import parse_user_query
from analyze_candidates import AnalyzeCandidates, ProductAnalyzer
from llm_provider import LLM
import numpy as np

def main():
    user_query_path = "user_query.txt"
    user_info_path = "user_info.xml"
    A_path = "product_A.html"
    B_path = "product_B.html"

    with open(user_query_path,"r",encoding='utf-8') as f:
        user_query = f.read()
    with open(user_info_path,"r",encoding='utf-8') as f:
        user_info_xml = f.read()
    options = [None, None]
    with open(A_path,"r",encoding='utf-8') as f:
        html = f.read()
        options[0] = AmazonProvider.parse_webpage(html)
    with open(B_path,"r",encoding='utf-8') as f:
        html = f.read()
        options[1] = AmazonProvider.parse_webpage(html)
    
    requirements = parse_user_query(user_query=user_query,user_info_xml=user_info_xml)
    analyzer = AnalyzeCandidates(requirements=requirements, options=options)
    analyzer.generate_summaries()
    result = analyzer.compare(analyzer.options[0], analyzer.options[1], include_reason=True)

    cmp_th = ''
    cmp_tr_a = ''
    cmp_tr_b = ''
    for field in ProductAnalyzer.fields:
        cmp_th += f'<th>{field}</th>'
        cmp_tr_a += f'<td>{analyzer.options[0]['details'].get(field,'Not found')}</td>'
        cmp_tr_b += f'<td>{analyzer.options[1]['details'].get(field,'Not found')}</td>'

    output_xml = ''
    for option in analyzer.options:
        output_xml += f'''
        <product link='{option.get('link', '')}'>
            <name>{option['name']}</name>
            <source>{option['source']}</source>
            <pros>{option['pros_summary']}</pros>
            <cons>{option['cons_summary']}</cons>
            <summary>{option['short_summary']}</summary>
            <reviews>{option['reviews_summary']}</reviews>
            <cmp>{option['comparison']}</cmp>
        </product>
        '''

    a_em = LLM.embed('"A" is the better product.')
    b_em = LLM.embed('"B" is the better product.')
    res_em = LLM.embed(result)
    winner = int((np.dot(a_em,res_em)/np.linalg.norm(a_em)) > (np.dot(b_em,res_em)/np.linalg.norm(b_em)))

    #format the output:
    output_html = f'''
    <table id=comparisonTable>
    <tr>{cmp_th}</tr>
    <tr>{cmp_tr_a}</tr>
    <tr>{cmp_tr_b}</tr>
    </table><br><br>
    <div id=info_xml hidden>
    {output_xml}
    </div>
    <div id=verdict>
    <span id=choice> <b><u>VERDICT:</u></b> Choose {options[winner]['name']}</span><br><br>
    <span id=reason>
    <b>WHY?</b><br>
    {result.replace('Product A', options[0]['name']).replace('Product B', options[1]['name'])}
    </span>
    </div>
    '''

    with open('output.html','w',encoding='utf-8') as f:
        f.write(output_html)

main()