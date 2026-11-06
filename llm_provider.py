import os
import ollama

os.environ["OLLAMA_API_KEY"] = 'fa0212eabb9a48cbafbce95eaa32bb22.xArP9pc7qYnyKNAjBgyr82Ur'

class LLM:
  MODEL = 'gemma3:1b'
  EMBEDDINGMODEL = 'all-minilm'
  
  @classmethod
  def embed(cls, q):
    return ollama.embed(model=LLM.EMBEDDINGMODEL, input=q).embeddings[0]
  
  @classmethod
  def embed_batch(cls, q_array):
    return ollama.embed(model=LLM.EMBEDDINGMODEL, input=q_array).embeddings

  @classmethod
  def generate(cls, user_prompt, system_prompt=None, **kwargs):
    print(f"PROMPTED: {user_prompt[0:200]}")
    msgs = [{'role': 'user','content': user_prompt}]
    if system_prompt is not None:
      msgs.insert(0, {'role': 'system','content': system_prompt})
    response = ollama.chat(model=LLM.MODEL, messages=msgs, **kwargs)
    print(f"RESPONSE: {response.message.content}")
    return response.message.content

  @classmethod
  def chat(cls, msgs, **kwargs):
    print(f"CHATS: {msgs[-1]['content'][0:200]}")
    response = ollama.chat(model=LLM.MODEL, messages=msgs, **kwargs)
    print(f"RESPONSE: {response.message.content}")
    return response.message.content

  @classmethod
  def desc_img(cls, content, img_paths, **kwargs):
    response = chat(model=LLM.MODEL, messages=[{'role': 'user', 'content': content, 'images': img_paths}], **kwargs)
    return response.message.content
  
  @classmethod
  def websearch(cls, q):
    return LLM.generate(user_prompt=q)
    response = ollama.web_search(q, max_results=1)
    return response[0].content

  def gen_batch(self, queries: list[str]):
    pass