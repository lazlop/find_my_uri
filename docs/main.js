import { pipeline } from 'https://cdn.jsdelivr.net/npm/@xenova/transformers@2.17.1';

document.addEventListener('DOMContentLoaded', async () => {
    const queryInput = document.getElementById('query');
    const namespaceSelect = document.getElementById('namespace');
    const nResultsInput = document.getElementById('n_results');
    const searchButton = document.getElementById('search');
    const statusDiv = document.getElementById('status');
    const resultsDiv = document.getElementById('results');

    statusDiv.textContent = 'Loading data files...';

    // Load the JSON data files
    const metadataResponse = await fetch('data/metadata.json');
    const metadata = await metadataResponse.json();

    const embeddingsResponse = await fetch('data/embeddings.json');
    const embeddings = await embeddingsResponse.json();

    statusDiv.textContent = 'Loading sentence transformer model...';

    // Load the sentence transformer model
    const extractor = await pipeline('feature-extraction', 'Xenova/paraphrase-MiniLM-L3-v2');

    statusDiv.textContent = 'Ready to search.';

    function cosineSimilarity(vecA, vecB) {
        let dotProduct = 0.0;
        let normA = 0.0;
        let normB = 0.0;
        for (let i = 0; i < vecA.length; i++) {
            dotProduct += vecA[i] * vecB[i];
            normA += vecA[i] * vecA[i];
            normB += vecB[i] * vecB[i];
        }
        return dotProduct / (Math.sqrt(normA) * Math.sqrt(normB));
    }

    searchButton.addEventListener('click', async () => {
        performSearch();
    });

    queryInput.addEventListener('keydown', (event) => {
        if (event.key === 'Enter') {
            performSearch();
        }
    });

    async function performSearch() {
        const query = queryInput.value;
        const namespace = namespaceSelect.value;

        if (!query) {
            alert('Please enter a search term');
            return;
        }

        statusDiv.textContent = 'Generating query embedding...';

        // Generate the query embedding
        const output = await extractor(query, { pooling: 'mean', normalize: true });
        const queryEmbedding = Array.from(output.data);

        statusDiv.textContent = 'Searching for similar URIs...';

        let filteredEmbeddings = embeddings;
        let filteredMetadata = metadata;

        if (namespace) {
            const namespaceURI = {
                "S223": "http://data.ashrae.org/standard223#",
                "WATR": "urn:nawi-water-ontology#",
                "UNIT": "http://qudt.org/vocab/unit/",
                "QK": "http://qudt.org/vocab/quantitykind/"
            }[namespace];

            const indices = metadata.map((m, i) => m.namespace === namespaceURI ? i : -1).filter(i => i !== -1);
            filteredEmbeddings = indices.map(i => embeddings[i]);
            filteredMetadata = indices.map(i => metadata[i]);
        }

        const similarities = filteredEmbeddings.map(embedding => cosineSimilarity(queryEmbedding, embedding));

        const nResults = parseInt(nResultsInput.value, 10);

        const topk = similarities.map((similarity, index) => ({ similarity, index }))
                               .sort((a, b) => b.similarity - a.similarity)
                               .slice(0, nResults);

        statusDiv.textContent = 'Search complete.';

        resultsDiv.innerHTML = '';
        if (topk.length === 0) {
            resultsDiv.innerHTML = '<p>No results found.</p>';
            return;
        }

        topk.forEach(result => {
            const match = filteredMetadata[result.index];
            const item = document.createElement('div');
            item.className = 'result-item';
            item.innerHTML = `
                <p><a href="${match.uri}" target="_blank">${match.local_name}</a></p>
                <p><strong>Label:</strong> ${match.label}</p>
                <p><strong>Comment:</strong> ${match.comment}</p>
                <p><strong>Namespace:</strong> ${match.namespace}</p>
            `;
            resultsDiv.appendChild(item);
        });
    }
});