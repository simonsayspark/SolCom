# 📅 Timeline Interativa de Compras 

Uma aplicação Streamlit para visualização interativa e otimização de compras com base em MOQ (Minimum Order Quantity).

## 🚀 Funcionalidades

- **📊 Análise de Timeline**: Visualização de quando o estoque vai acabar
- **🎯 Otimização de MOQ**: Cálculo automático de quantidades ideais de compra
- **📈 Gráficos Interativos**: Visualizações dinâmicas com Plotly
- **🔍 Filtros Inteligentes**: Filtragem por urgência (Crítico, Médio, Atenção, OK)
- **💰 Cálculos Financeiros**: Investimento total e análise de custos
- **📁 Upload Seguro**: Carregue seus próprios dados sem comprometer informações sensíveis

## 🛠️ Como Usar

### 1. Executar Localmente
```bash
pip install -r requirements.txt
python -m streamlit run app.py
```

### 2. Upload de Dados
- Faça upload do seu arquivo Excel na barra lateral
- Ou use os dados de exemplo para testar a aplicação

### 3. Formato do Arquivo Excel
Seu arquivo deve conter as seguintes colunas:
- **Item**: Código do item
- **Modelo**: Nome/modelo do produto
- **Fornecedor**: Nome do fornecedor
- **QTD**: Quantidade 
- **Preço FOB Unitário**: Preço unitário
- **Estoque Total**: Quantidade em estoque
- **In Transit Shipt**: Quantidade em trânsito
- **Avg Sales**: Vendas médias mensais
- **CBM**: Volume em metros cúbicos
- **MOQ**: Quantidade mínima de pedido

> ⚠️ **Importante**: Os dados devem começar na linha 10 do Excel (header=9)

## 🔒 Segurança dos Dados

Esta aplicação foi projetada para proteger suas informações sensíveis:
- ✅ **Sem armazenamento**: Os dados não são salvos no servidor
- ✅ **Upload temporário**: Arquivos são processados apenas na sessão
- ✅ **Dados de exemplo**: Use dados fictícios para demonstração
- ✅ **Local first**: Funciona com dados locais para desenvolvimento

## 📊 Métricas Calculadas

- **🔴 Críticos**: Produtos com menos de 1 mês de estoque
- **🟠 Médios**: Produtos com 1-3 meses de estoque  
- **🟡 Atenção**: Produtos com 3-6 meses de estoque
- **🟢 OK**: Produtos com mais de 6 meses de estoque

## 🎛️ Controles

- **Meta (meses)**: Ajuste quantos meses de estoque manter
- **Filtros**: Visualize apenas produtos de determinada urgência
- **Zoom**: Use as ferramentas do gráfico para zoom e navegação

## 📦 Dependências

- streamlit>=1.28.0
- pandas>=2.0.0
- plotly>=5.15.0
- numpy>=1.24.0
- openpyxl>=3.1.0

## 🚀 Deploy

A aplicação pode ser facilmente deployada em:
- Streamlit Cloud
- Heroku
- AWS/GCP/Azure
- Qualquer servidor com Python

## 📝 Licença

Este projeto está sob licença MIT.

## 🤝 Contribuições

Contribuições são bem-vindas! Sinta-se à vontade para:
- Reportar bugs
- Sugerir novas funcionalidades
- Enviar pull requests

---
Desenvolvido com ❤️ para otimização de compras 