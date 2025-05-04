from app.services.llm_endpoint import generate_prediction

prompt = "Apple just launched its new product. What will be the stock price in coming week?"
result = generate_prediction(prompt)
print(result)