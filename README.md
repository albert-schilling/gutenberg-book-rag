# Book RAG Project

A one-day project with eight books from Project Gutenberg. Every group builds a retrieval-augmented generation (RAG) system for one book with LangChain: clean the text, split it into chunks, store their embeddings in Chroma, and answer questions with `gpt-oss-20b` on Groq, showing the passages of the book that each answer is based on.

## Learning Objectives

By the end of this project, you should be able to:

- Clean a raw Project Gutenberg book with regular expressions, and split it into chunks that keep their position in the book.
- Store the embeddings of the chunks in a Chroma vector store, and retrieve the passages that are closest to a question.
- Build a RAG chain with the LangChain Expression Language that answers questions with a language model on Groq, only from the retrieved passages, and returns the passages it used.

## Learning Path

| File | Description |
|---|---|
| [**01 - Book RAG Project**](01_book_rag_project.ipynb) | The project: the business problem, the description of the eight books and the task in seven steps. |
| [**Command-Line Tool**](rag_cli.py) | The last step: turn your RAG system into a tool that answers questions about your book in the terminal. |

### Additional Folders and Files

| File / Folder | Description |
|---|---|
| [**Assets**](assets/) | The diagram of the project's steps shown in the notebook, with its Mermaid source in `assets/diagrams/`. |
| [**Data**](data/) | The eight books as plain text files, exactly as Project Gutenberg distributes them, with a list of their sources in `data/README.md`. |
| [**.env.example**](.env.example) | The template for your `.env` file with the Groq API key. |
| [**pyproject.toml**](pyproject.toml) | Project configuration and dependencies. |
| [**uv.lock**](uv.lock) | Dependency lock file. |

## Books and Groups

Every group works on one book: find your group number in the table below.

| Group | Book | File |
|---|---|---|
| Group 1 | The Adventures of Pinocchio | `adventures_of_pinocchio_collodi.txt` |
| Group 2 | The Adventures of Sherlock Holmes | `adventures_of_sherlock_holmes_doyle.txt` |
| Group 3 | Antarctic Penguins | `antarctic_penguins_levick.txt` |
| Group 4 | Climate, Considered Especially in Relation to Man | `climate_in_relation_to_man_ward.txt` |
| Group 5 | Frankenstein | `frankenstein_shelley.txt` |
| Group 6 | The Time Machine | `the_time_machine_wells.txt` |
| Group 7 | Tom Brown's School Days | `tom_browns_school_days_hughes.txt` |
| Group 8 | The Wonderful Wizard of Oz | `wonderful_wizard_of_oz_baum.txt` |

## Setup

> [!NOTE]
> Throughout these steps, text in angle brackets like `<repo-name>` is a **placeholder**. Replace it, including the `< >` brackets, with your own value. For example, `cd <repo-name>` becomes `cd my-book-rag-project`.

### 1. Create the Repository from the Template

Click **Use this template** on GitHub.

When creating the repository:

- Set yourself as the **Owner**
- Choose a repository name
- Disable **Include all branches**
- Click **Create repository**

> [!IMPORTANT]
> If you are working in pairs or groups, only **one person** should complete this step.

---

### 2. Add Collaborators (Pairs/Groups Only)

If working with teammates:

1. Open the repository on GitHub
2. Go to **Settings → Collaborators**
3. Add your teammates as collaborators
4. Share the repository link with your team

Teammates should accept the invitation before continuing.

---

### 3. Clone the Repository

Copy the SSH URL from the **Code** button on GitHub, then run:

```bash
git clone <copied-ssh-url>
```

The copied SSH URL will look like `git@github.com:<your-username>/<repo-name>.git`.

---

### 4. Move into the Project Folder and Install Dependencies

This installs all dependencies, including LangChain, Chroma and sentence-transformers, and creates a virtual environment in `.venv/`. sentence-transformers installs PyTorch, a large package, so the first install takes a few minutes.

```bash
cd <repo-name>
uv sync
```

---

### 5. Add Your Groq API Key

The language model runs on [Groq](https://groq.com/), which needs an API key. Copy the example file first:

```bash
cp .env.example .env
```

Then open `.env` and paste a key after `GROQ_API_KEY=`. The notebook reads it with `load_dotenv()`. You can get the key in one of two ways:

- **Reuse your key from the LLM Engineering notebooks.** If you created a Groq API key the day before, copy it from the `.env` file of that repository. One key works for any number of repositories.
- **Create a new key.** Sign up or log in at [console.groq.com](https://console.groq.com/), open the [API Keys page](https://console.groq.com/keys), click **Create API Key**, give it a name and copy it. Groq shows the key only once.

> [!CAUTION]
> Never commit your `.env` file. It contains your personal API key, and anyone who can read the repository could use it. `.env` is listed in `.gitignore`, so Git ignores it as long as you do not add it by force.

---

### 6. Open the Notebook

> [!NOTE]
> Make sure you open VS Code from the project root so it automatically detects the environment created by `uv sync`.

Launch VS Code in the project root folder:

```bash
code .
```

Then open the notebook and select the Python environment created by `uv sync` as the kernel.

## Run the Command-Line Tool

When your RAG system works in the notebook, copy its code into [`rag_cli.py`](rag_cli.py) and complete the loop described in the comments. Then run it from the project root:

```bash
uv run python rag_cli.py
```

Type a question and press Enter: the tool prints the answer and the passage of the book it is based on. Type `quit` to exit.

> [!TIP]
> Build the vector store only when it is empty. Otherwise the tool embeds your book again every time it starts, and each start takes as long as the first one.

## Data and Credits

The books are part of the repository, in `data/` (3 MB). The embedding model `sentence-transformers/all-MiniLM-L6-v2` (90 MB) is downloaded from Hugging Face the first time you create the embeddings, and stored in `~/.cache/huggingface`. The Chroma vector store is saved in `chroma_db/`, which Git ignores, because you can rebuild it from the books at any time.

- **Books**: eight books from [Project Gutenberg](https://www.gutenberg.org/), public domain in the United States. Their sources are listed in [`data/README.md`](data/README.md), and the [Project Gutenberg licence](https://www.gutenberg.org/policy/license.html) is at the end of every file.

## References & Further Reading

- [**LangChain: Build a semantic search engine**](https://docs.langchain.com/oss/python/langchain/knowledge-base): Loading documents, splitting them into chunks, embedding them and searching a vector store.
- [**LangChain: Recursive text splitter**](https://docs.langchain.com/oss/python/integrations/splitters/recursive_text_splitter): How `RecursiveCharacterTextSplitter` splits text by paragraphs, lines and words.
- [**LangChain: Chroma integration**](https://docs.langchain.com/oss/python/integrations/vectorstores/chroma): Creating a Chroma vector store, adding documents with ids and turning it into a retriever.
- [**LangChain: ChatGroq**](https://docs.langchain.com/oss/python/integrations/chat/groq): Using models hosted on Groq in LangChain.
- [**Groq: Supported models**](https://console.groq.com/docs/models): The models available on Groq, with their limits.
- [**Sentence Transformers: Pretrained models**](https://www.sbert.net/docs/sentence_transformer/pretrained_models.html): Other embedding models to try, with their speed and quality.
- [**Lewis et al. (2020), Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks**](https://arxiv.org/abs/2005.11401): The paper that introduced RAG.
