import { useState } from 'preact/hooks';
import styles from './CoffeeSearch.module.css';

export function CoffeeSearch({ apiFetch, onResult }) {
  const [mode, setMode] = useState('search');
  const [query, setQuery] = useState('');
  const [bagText, setBagText] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSearch = async () => {
    if (!query.trim()) return;
    setLoading(true);
    setError('');
    try {
      const data = await apiFetch('/search-coffee', {
        method: 'POST',
        body: JSON.stringify({ query: query.trim() }),
      });
      onResult(data);
    } catch (err) {
      setError(err.message || 'Search failed');
    } finally {
      setLoading(false);
    }
  };

  const handleParse = async () => {
    if (!bagText.trim()) return;
    setLoading(true);
    setError('');
    try {
      const data = await apiFetch('/parse-bag', {
        method: 'POST',
        body: JSON.stringify({ text: bagText.trim() }),
      });
      onResult(data);
    } catch (err) {
      setError(err.message || 'Parsing failed');
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') handleSearch();
  };

  return (
    <div class={styles.section}>
      <div class={styles.tabs}>
        <button
          class={`${styles.tab} ${mode === 'search' ? styles.tabActive : ''}`}
          onClick={() => setMode('search')}
        >
          Search
        </button>
        <button
          class={`${styles.tab} ${mode === 'paste' ? styles.tabActive : ''}`}
          onClick={() => setMode('paste')}
        >
          Paste bag info
        </button>
      </div>

      {mode === 'search' ? (
        <div class={styles.searchRow}>
          <input
            class={styles.input}
            type="text"
            placeholder="Coffee name or roaster..."
            value={query}
            onInput={e => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={loading}
          />
          <button class={styles.submitBtn} onClick={handleSearch} disabled={loading}>
            Search
          </button>
        </div>
      ) : (
        <div class={styles.pasteArea}>
          <textarea
            class={styles.textarea}
            placeholder="Paste bag label text, product page URL, or any coffee description..."
            value={bagText}
            onInput={e => setBagText(e.target.value)}
            disabled={loading}
          />
          <button class={styles.submitBtn} onClick={handleParse} disabled={loading}>
            Parse with AI
          </button>
        </div>
      )}

      {loading && (
        <div class={styles.status}>
          <span class={styles.spinner} />
          <span>Identifying coffee...</span>
        </div>
      )}

      {error && <p class={styles.error}>{error}</p>}
    </div>
  );
}
