from website_provider import AmazonProvider
from options_finder import parse_user_query, find_options
from select_top_k import selector
from analyze_candidates import AnalyzeCandidates
import webbrowser
import json
import random

def run_search(user_query):
    user_info_path = "user_info.xml"
    with open(user_info_path,"r",encoding='utf-8') as f:
        user_info_xml = f.read()
    requirements = parse_user_query(user_query=user_query,user_info_xml=user_info_xml)
    providers = [AmazonProvider]
    all_options = find_options(requirements=requirements,providers=providers)
    print('all options found')
    top_selector = selector(requirements=requirements,options=all_options)
    top_options = top_selector.select()
    analyzer = AnalyzeCandidates(requirements=requirements, options=top_options)
    analyzer.generate_summaries()
    analyzer.analyze()

    output_json = []
    for option in analyzer.options:
        output_json.append({
            'store': option['source'],
            'color': f"#{random.randint(0, 0xFFFFFF):06x}",
            'initial': option['source'][0],
            'title': option['name'],
            'description': option['short_summary'],
            'pros': option['pros_summary'],
            'cons': option['cons_summary'],
            'reviews_summary': option['reviews_summary'],
            'price': f"₹{option['price']:,.2f}",
            'meta': f"{option['rating']}★ · {option['ratings_count']} ratings",
            'link': option['link'],
            'comparison': option['comparison'], 
        })

    json_str = json.dumps(output_json)
    return json_str

from http.server import SimpleHTTPRequestHandler, HTTPServer

HOST = "localhost"
PORT = 8000


class Handler(SimpleHTTPRequestHandler):
    def do_POST(self):
        # Read the request body
        content_length = int(self.headers.get("Content-Length", 0))
        query = (self.rfile.read(content_length) if content_length else b"").decode('utf-8')

        print(f"Received POST to {self.path}: {query}")
        try:
            body = run_search(query)
        except RuntimeError as e:
            self.send_error(
                500, 
                message="Internal Error", 
                explain="Internal fetch request was denied."
            )
            print(f'ERROR: {str(e)}')
            return

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        # Allow index.html served from the same origin (and elsewhere) to POST here
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body.encode('utf-8'))

    def do_OPTIONS(self):
        # Handle CORS preflight requests
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def log_message(self, format, *args):
        # Slightly quieter default logging
        print("%s - %s" % (self.address_string(), format % args))


if __name__ == "__main__":
    server = HTTPServer((HOST, PORT), Handler)
    print(f"Serving on http://{HOST}:{PORT}  (Ctrl+C to stop)")
    webbrowser.open(f'http://{HOST}:{PORT}')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.server_close()

'''
JUNK CODE

output_xml = ''
    for option in analyzer.options:
        output_xml += f
        <product link='{option['link']}'>
            <name>{option['name']}</name>
            <source>{option['source']}</source>
            <pros>{option['pros_summary']}</pros>
            <cons>{option['cons_summary']}</cons>
            <summary>{option['short_summary']}</summary>
            <reviews>{option['reviews_summary']}</reviews>
            <cmp>{option['comparison']}</cmp>
        </product>
        

    with open('output.xml','w',encoding='utf-8') as f:
        f.write(output_xml)
'''