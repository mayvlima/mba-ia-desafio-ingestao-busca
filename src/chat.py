import os
from dotenv import load_dotenv
from search import search_prompt
from langchain_postgres import PGVector
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_openai import OpenAIEmbeddings
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

def get_embedding_model():
    if os.getenv("GOOGLE_API_KEY"):
        return GoogleGenerativeAIEmbeddings(model=os.getenv("GOOGLE_EMBEDDING_MODEL"))
    return OpenAIEmbeddings(model=os.getenv("OPENAI_EMBEDDING_MODEL"))

def get_llm():
    if os.getenv("GOOGLE_API_KEY"):
        return ChatGoogleGenerativeAI(model=os.getenv("GOOGLE_CHAT_MODEL", "gemini-2.5-flash-lite"))
    return ChatOpenAI(model=os.getenv("OPENAI_CHAT_MODEL", "gpt-5-nano"))

def validate_env():
    if not (os.getenv("GOOGLE_API_KEY") or os.getenv("OPENAI_API_KEY")):
        raise RuntimeError("At least one of GOOGLE_API_KEY or OPENAI_API_KEY must be set")
    for k in ("DATABASE_URL", "PG_VECTOR_COLLECTION_NAME"):
        if not os.getenv(k):
            raise RuntimeError(f"Environment variable {k} is not set")

def main():
    load_dotenv()
    
    try:
        validate_env()
    except RuntimeError as e:
        print(f"Erro: {e}")
        return

    embedding_model = get_embedding_model()
    
    store = PGVector(
        embeddings=embedding_model,
        collection_name=os.getenv("PG_VECTOR_COLLECTION_NAME"),
        connection=os.getenv("DATABASE_URL"),
        use_jsonb=True,
    )
    
    llm = get_llm()
    
    chain = search_prompt(llm)

    if not chain:
        print("Não foi possível iniciar o chat. Verifique os erros de inicialização.")
        return
    
    print("=== Chat de Perguntas e Respostas ===")
    print("Digite 'sair' para encerrar o chat")
    
    while True:
        pergunta = input("\nSua pergunta: ")

        if pergunta.lower() in ["sair", "exit", "quit"]:
            print("Encerrando o chat. Até logo!")
            break
        
        try:
            result = store.similarity_search_with_score(pergunta, k=15)
            
            documentos = [doc for doc, score in result]
      
            contexto = "\n".join([doc.page_content for doc in documentos])

            answer = chain.invoke({"contexto": contexto, "pergunta": pergunta})

            print("\nResposta:")
            print(answer)
            print("-"*90)
            print("-"*90)

        except Exception as e:
            print(f"\nOcorreu um erro ao processar sua pergunta: {e}")
            print("-"*90)
            print("-"*90)

if __name__ == "__main__":
    main()