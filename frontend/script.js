const API = {
  search: (params) => fetch(`/api/books/search${params}`),
  details: (id) => fetch(`/api/books/${id}`),
  similar: (id) => fetch(`/api/books/${id}/similar`),
  register: (payload) => fetch(`/api/auth/register`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) }),
  login: (payload) => fetch(`/api/auth/login`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) }),
  favorites: {
    list: () => fetch(`/api/favorites/`, { headers: authHeader() }),
    add: (fav) => fetch(`/api/favorites/`, { method: 'POST', headers: { 'Content-Type': 'application/json', ...authHeader() }, body: JSON.stringify(fav) }),
    remove: (id) => fetch(`/api/favorites/${id}`, { method: 'DELETE', headers: authHeader() }),
  }
};

function authHeader() {
  const t = localStorage.getItem('token');
  return t ? { 'Authorization': `Bearer ${t}` } : {};
}

function navigate(hash) {
  window.location.hash = hash;
}

function setActiveNav() {
  const h = window.location.hash || '#home';
  document.querySelectorAll('.nav a').forEach(a => a.classList.toggle('active', a.getAttribute('href') === h));
  document.querySelectorAll('.view-section').forEach(s => s.classList.toggle('active', `#${s.id}` === h));
}
window.addEventListener('hashchange', setActiveNav);

// Dark / Light Mode
const modeBtn = document.getElementById('modeToggle');
modeBtn.addEventListener('click', () => {
  const html = document.documentElement;
  const isDark = html.getAttribute('data-theme') === 'dark';
  html.setAttribute('data-theme', isDark ? 'light' : 'dark');
  modeBtn.textContent = isDark ? '☀️' : '🌙';
});

// Mood Filters - Support multiple selection
const moodTags = document.getElementById('moodTags');
let selectedMoods = new Set();
if (moodTags) {
  moodTags.querySelectorAll('button').forEach(b => {
    b.addEventListener('click', () => {
      const m = b.dataset.mood;
      // Toggle mood selection (can select multiple moods)
      if (selectedMoods.has(m)) {
        selectedMoods.delete(m);
        b.classList.remove('active');
      } else {
        selectedMoods.add(m);
        b.classList.add('active');
      }
    });
  });
}

let startIndex = 0;
const maxResults = 40;

function buildParams() {
  const q = new URLSearchParams();
  const v = id => document.getElementById(id)?.value || '';

  // Support ALL filter combinations simultaneously
  const filters = [
    ['query', v('fQuery')],
    ['author', v('fAuthor')],
    ['genre', v('fGenre')],
    ['language', v('fLanguage')],
    ['min_rating', v('fRating')],
    ['year', v('fYear')],
    ['reading_level', v('fReadingLevel')],
    ['length', v('fLength')],
    ['mood', selectedMoods.size > 0 ? Array.from(selectedMoods).join(',') : ''],
  ];

  // Add ALL active filters to the query
  filters.forEach(([key, value]) => {
    if (value && value.trim() !== '') {
      q.set(key, value.trim());
    }
  });

  q.set('start_index', startIndex);
  q.set('max_results', maxResults);
  return `?${q.toString()}`;
}

function isPlaceholderThumbnail(url) {
  if (!url) return true;
  // Reduced patterns to minimize false positives for real covers
  const genericPatterns = [
    'blank_book',
    'no_image_found',
    'image_not_available'
  ];
  return genericPatterns.some(p => url.toLowerCase().includes(p.toLowerCase()));
}

function renderCard(container, b) {
  const tpl = document.getElementById('bookCardTpl');
  const el = tpl.content.cloneNode(true);

  const coverImg = el.querySelector('.cover');
  const hasValidThumbnail = b.thumbnail && !isPlaceholderThumbnail(b.thumbnail);

  if (hasValidThumbnail) {
    coverImg.src = b.thumbnail;
    coverImg.onerror = () => {
      // If the image fails to load (404, etc.), fallback to animated placeholder
      coverImg.replaceWith(createPlaceholder(b.title));
    };
  } else {
    // No thumbnail or obviously generic placeholder: Use stylized CSS cover
    coverImg.replaceWith(createPlaceholder(b.title));
  }

  el.querySelector('.title').textContent = b.title;
  // Format author and publication year if available
  const authorsText = (b.authors || []).join(', ');
  const yearText = b.published_year ? ` (${b.published_year})` : '';
  el.querySelector('.author').textContent = (authorsText || 'Unknown Author') + yearText;

  const descEl = el.querySelector('.desc');
  if (b.description) {
    descEl.textContent = b.description;
  } else {
    descEl.textContent = 'No description available for this book.';
    descEl.style.fontStyle = 'italic';
    descEl.style.opacity = '0.6';
  }

  // Format the rating with stars if available
  if (b.average_rating && b.average_rating !== 'N/A') {
    const roundedRating = Math.round(b.average_rating * 10) / 10; // Round to 1 decimal place
    const fullStars = Math.floor(roundedRating);
    const halfStar = roundedRating % 1 >= 0.5 ? 1 : 0;
    const emptyStars = 5 - fullStars - halfStar;

    let starDisplay = '';
    for (let i = 0; i < fullStars; i++) starDisplay += '★';
    if (halfStar) starDisplay += '☆'; // Using half star as ☆, could use ½ symbol
    for (let i = 0; i < emptyStars; i++) starDisplay += '☆';

    el.querySelector('.rating').textContent = `${starDisplay} (${roundedRating})`;
  } else {
    el.querySelector('.rating').textContent = 'Rating: N/A';
  }
  el.querySelector('.confidence').textContent = `Confidence: ${b.confidence_pct ?? Math.round(b.score * 100)}%`;

  const reasonsEl = el.querySelector('.reasons');
  (b.reasons || []).forEach(r => {
    const li = document.createElement('li'); li.textContent = r; reasonsEl.appendChild(li);
  });

  el.querySelector('.readMore').addEventListener('click', async () => {
    navigate('#details');
    await showBookDetails(b.id);
  });

  el.querySelector('.similar').addEventListener('click', async () => {
    const res = await API.similar(b.id);
    const data = await res.json();
    const grid = document.getElementById('results');
    navigate('#browse'); // Ensure we go to the results page
    grid.innerHTML = '';
    data.items.forEach(i => renderCard(grid, i));
  });

  const favBtn = el.querySelector('.favorite');
  const isFavView = container.id === 'favoritesGrid';
  favBtn.textContent = isFavView ? 'Remove from favorites' : 'Save to favorites';
  favBtn.addEventListener('click', async () => {
    const token = localStorage.getItem('token');
    if (!token) { alert('Login to manage favorites.'); navigate('#profile'); return; }
    if (isFavView) {
      const r = await API.favorites.remove(b.id);
      if (r.ok) { alert('Removed from favorites'); loadFavorites(); } else { alert('Could not remove'); }
    } else {
      const r = await API.favorites.add({ book_id: b.id, book_json: b });
      if (r.ok) alert('Saved to favorites'); else alert('Could not save');
    }
  });

  container.appendChild(el);
}

// State variables to track loaded books for each section
const sectionState = {
  topRated: { loaded: [], startIndex: 0, maxResults: 10 },
  recentlyAdded: { loaded: [], startIndex: 0, maxResults: 10 },
  popularBooks: { loaded: [], startIndex: 0, maxResults: 10 },
  fictionBooks: { loaded: [], startIndex: 0, maxResults: 10 },
  islamicBooks: { loaded: [], startIndex: 0, maxResults: 10 },
  southAsianBooks: { loaded: [], startIndex: 0, maxResults: 10 },
  globalBooks: { loaded: [], startIndex: 0, maxResults: 10 },
  scienceTechBooks: { loaded: [], startIndex: 0, maxResults: 10 },
  historyPhilosophyBooks: { loaded: [], startIndex: 0, maxResults: 10 }
};

async function loadTopRated(loadMore = false) {
  const grid = document.getElementById('topRated');
  if (!grid) return;

  if (!loadMore) {
    sectionState.topRated.loaded = [];
    sectionState.topRated.startIndex = 0;
    grid.innerHTML = '';
  }

  const startIndex = sectionState.topRated.startIndex;
  const maxResults = sectionState.topRated.maxResults;

  // No changes needed here, just ensuring maxResults is high
  const res = await API.search(`?query=best books&start_index=${startIndex}&max_results=${maxResults}`);
  const data = await res.json();

  data.forEach(b => {
    renderCard(grid, b);
    sectionState.topRated.loaded.push(b);
  });

  sectionState.topRated.startIndex += maxResults;
}

async function loadRecentlyAdded(loadMore = false) {
  const grid = document.getElementById('recentlyAdded');
  if (!grid) return;

  if (!loadMore) {
    sectionState.recentlyAdded.loaded = [];
    sectionState.recentlyAdded.startIndex = 0;
    grid.innerHTML = '';
  }

  const startIndex = sectionState.recentlyAdded.startIndex;
  const maxResults = sectionState.recentlyAdded.maxResults;

  const res = await API.search(`?query=new books&start_index=${startIndex}&max_results=${maxResults}`);
  const data = await res.json();

  data.sort((a, b) => (b.published_year || 0) - (a.published_year || 0));
  data.forEach(b => {
    renderCard(grid, b);
    sectionState.recentlyAdded.loaded.push(b);
  });

  sectionState.recentlyAdded.startIndex += maxResults;
}

// Function to load popular books
async function loadPopularBooks(loadMore = false) {
  const grid = document.getElementById('popularBooks');
  if (!grid) return;

  if (!loadMore) {
    sectionState.popularBooks.loaded = [];
    sectionState.popularBooks.startIndex = 0;
    grid.innerHTML = '';
  }

  const startIndex = sectionState.popularBooks.startIndex;
  const maxResults = sectionState.popularBooks.maxResults;

  const res = await API.search(`?query=popular books&start_index=${startIndex}&max_results=${maxResults}`);
  const data = await res.json();

  data.forEach(b => {
    renderCard(grid, b);
    sectionState.popularBooks.loaded.push(b);
  });

  sectionState.popularBooks.startIndex += maxResults;
}

// Function to load fiction books
async function loadFictionBooks(loadMore = false) {
  const grid = document.getElementById('fictionBooks');
  if (!grid) return;

  if (!loadMore) {
    sectionState.fictionBooks.loaded = [];
    sectionState.fictionBooks.startIndex = 0;
    grid.innerHTML = '';
  }

  const startIndex = sectionState.fictionBooks.startIndex;
  const maxResults = sectionState.fictionBooks.maxResults;

  const res = await API.search(`?genre=Fiction&start_index=${startIndex}&max_results=${maxResults}`);
  const data = await res.json();

  data.forEach(b => {
    renderCard(grid, b);
    sectionState.fictionBooks.loaded.push(b);
  });

  sectionState.fictionBooks.startIndex += maxResults;
}

// Function to load Islamic books
async function loadIslamicBooks(loadMore = false) {
  const grid = document.getElementById('islamicBooks');
  if (!grid) return;

  if (!loadMore) {
    sectionState.islamicBooks.loaded = [];
    sectionState.islamicBooks.startIndex = 0;
    grid.innerHTML = '';
  }

  const startIndex = sectionState.islamicBooks.startIndex;
  const maxResults = sectionState.islamicBooks.maxResults;

  const res = await API.search(`?genre=Islam&start_index=${startIndex}&max_results=${maxResults}`);
  const data = await res.json();

  data.forEach(b => {
    renderCard(grid, b);
    sectionState.islamicBooks.loaded.push(b);
  });

  sectionState.islamicBooks.startIndex += maxResults;
}

// Function to load South Asian books (Indian & Pakistani)
async function loadSouthAsianBooks(loadMore = false) {
  const grid = document.getElementById('southAsianBooks');
  if (!grid) return;

  if (!loadMore) {
    sectionState.southAsianBooks.loaded = [];
    sectionState.southAsianBooks.startIndex = 0;
    grid.innerHTML = '';
  }

  const startIndex = sectionState.southAsianBooks.startIndex;
  const maxResults = sectionState.southAsianBooks.maxResults;

  // Search for high-quality results from curated authors and topics
  const res = await API.search(`?query=Indian Pakistani literary fiction masterpieces classic&start_index=${startIndex}&max_results=${maxResults}`);
  const data = await res.json();

  data.forEach(b => {
    renderCard(grid, b);
    sectionState.southAsianBooks.loaded.push(b);
  });

  sectionState.southAsianBooks.startIndex += maxResults;
}

// Function to load Global Masterpieces
async function loadGlobalBooks(loadMore = false) {
  const grid = document.getElementById('globalBooks');
  if (!grid) return;
  if (!loadMore) { sectionState.globalBooks.loaded = []; sectionState.globalBooks.startIndex = 0; grid.innerHTML = ''; }
  const startIndex = sectionState.globalBooks.startIndex;
  const maxResults = sectionState.globalBooks.maxResults;
  const res = await API.search(`?query=classic world literature masterpieces&start_index=${startIndex}&max_results=${maxResults}`);
  const data = await res.json();
  data.forEach(b => { renderCard(grid, b); sectionState.globalBooks.loaded.push(b); });
  sectionState.globalBooks.startIndex += maxResults;
}

// Function to load Science & Technology
async function loadScienceTechBooks(loadMore = false) {
  const grid = document.getElementById('scienceTechBooks');
  if (!grid) return;
  if (!loadMore) { sectionState.scienceTechBooks.loaded = []; sectionState.scienceTechBooks.startIndex = 0; grid.innerHTML = ''; }
  const startIndex = sectionState.scienceTechBooks.startIndex;
  const maxResults = sectionState.scienceTechBooks.maxResults;
  const res = await API.search(`?query=science technology physics computing&start_index=${startIndex}&max_results=${maxResults}`);
  const data = await res.json();
  data.forEach(b => { renderCard(grid, b); sectionState.scienceTechBooks.loaded.push(b); });
  sectionState.scienceTechBooks.startIndex += maxResults;
}

// Function to load History & Philosophy
async function loadHistoryPhilosophyBooks(loadMore = false) {
  const grid = document.getElementById('historyPhilosophyBooks');
  if (!grid) return;
  if (!loadMore) { sectionState.historyPhilosophyBooks.loaded = []; sectionState.historyPhilosophyBooks.startIndex = 0; grid.innerHTML = ''; }
  const startIndex = sectionState.historyPhilosophyBooks.startIndex;
  const maxResults = sectionState.historyPhilosophyBooks.maxResults;
  const res = await API.search(`?query=world history philosophy ethics&start_index=${startIndex}&max_results=${maxResults}`);
  const data = await res.json();
  data.forEach(b => { renderCard(grid, b); sectionState.historyPhilosophyBooks.loaded.push(b); });
  sectionState.historyPhilosophyBooks.startIndex += maxResults;
}

async function searchAndRender(reset = false) {
  const grid = document.getElementById('results');
  if (reset) { grid.innerHTML = ''; startIndex = 0; }
  const params = buildParams();
  const res = await API.search(params + '&is_search=true');
  const data = await res.json();
  if (data.length === 0 && startIndex === 0) {
    grid.innerHTML = '<p class="no-results-msg">No results found for these filters. Try adjusting your settings!</p>';
    alert('No books found matching these filters. Try using fewer filters or a different genre!');
    return;
  }
  data.forEach(b => renderCard(grid, b));
}

// Apply and reset filters
const ratingInput = document.getElementById('fRating');
const ratingVal = document.getElementById('ratingVal');
if (ratingInput && ratingVal) {
  ratingInput.addEventListener('input', () => {
    ratingVal.textContent = ratingInput.value;
  });
}

const applyBtn = document.getElementById('applyFilters');
if (applyBtn) applyBtn.addEventListener('click', () => searchAndRender(true));
const resetBtn = document.getElementById('resetFilters');
if (resetBtn) resetBtn.addEventListener('click', () => {
  ['fQuery', 'fAuthor', 'fGenre', 'fLanguage', 'fYear', 'fRating', 'fReadingLevel', 'fLength'].forEach(id => {
    const el = document.getElementById(id); if (el) el.value = '';
  });
  selectedMoods.clear();
  moodTags.querySelectorAll('button').forEach(b => b.classList.remove('active'));
  if (ratingVal) ratingVal.textContent = '0';
  searchAndRender(true);
});

const loadMoreBtn = document.getElementById('loadMore');
if (loadMoreBtn) loadMoreBtn.addEventListener('click', () => { startIndex += maxResults; searchAndRender(false); });

// Auth
const loginBtn = document.getElementById('loginBtn');
if (loginBtn) loginBtn.addEventListener('click', async () => {
  const email = document.getElementById('loginEmail').value.trim();
  const password = document.getElementById('loginPassword').value;

  if (!email || !password) {
    alert('Missing Fields: Both email and password are required');
    return;
  }

  // Show loading state
  const originalText = loginBtn.textContent;
  loginBtn.textContent = 'Signing In...';
  loginBtn.disabled = true;

  try {
    const res = await API.login({ email, password });
    const data = await res.json();

    if (res.ok) {
      localStorage.setItem('token', data.access_token);
      alert('Successfully logged in!');
      updateUserStatus();
      loadFavorites();
      navigate('#profile');
    } else {
      let errorMessage = 'Login failed';

      if (res.status === 401) {
        errorMessage = 'Invalid Credentials: Please check your email and password';
      } else if (res.status === 503) {
        errorMessage = 'Service Unavailable: Database connection issues. Please try again later';
      } else if (!navigator.onLine) {
        errorMessage = 'Network Error: Please check your internet connection';
      } else {
        errorMessage = (data && data.detail) || 'Login failed. Please check your credentials.';
      }

      alert(errorMessage);
    }
  } catch (error) {
    console.error('Login error:', error);

    if (!navigator.onLine) {
      alert('Server Not Running: Please make sure the backend server is running on port 8000');
    } else {
      alert('Server Not Running: Unable to connect to the server. Please check if the backend is running on port 8000');
    }
  } finally {
    // Reset button state
    loginBtn.textContent = originalText;
    loginBtn.disabled = false;
  }
});

const registerBtn = document.getElementById('registerBtn');
if (registerBtn) registerBtn.addEventListener('click', async () => {
  const name = document.getElementById('regName').value.trim();
  const email = document.getElementById('regEmail').value.trim();
  const password = document.getElementById('regPassword').value;

  // Enhanced client-side validation
  if (!name || !email || !password) {
    alert('Missing Fields: All three fields (name, email, password) must be filled');
    return;
  }

  // Show loading state
  const originalText = registerBtn.textContent;
  registerBtn.textContent = 'Creating Account...';
  registerBtn.disabled = true;

  try {
    // Attempt registration
    const res = await API.register({ name, email, password });
    const data = await res.json().catch(() => ({}));

    if (res.ok) {
      // Auto-login after successful registration
      const loginRes = await API.login({ email, password });
      const loginData = await loginRes.json().catch(() => ({}));

      if (loginRes.ok) {
        localStorage.setItem('token', loginData.access_token);
        alert('Account created successfully! You are now logged in.');
        updateUserStatus();
        loadFavorites();
        navigate('#favorites');
      } else {
        alert((loginData && loginData.detail) || 'Account created. Please login manually.');
        navigate('#profile');
      }
    } else {
      // Handle different error types
      let errorMessage = 'Registration failed';

      if (res.status === 400) {
        errorMessage = data.detail || 'Please fill in all required fields';
      } else if (res.status === 409) {
        errorMessage = 'Email Already Exists: This email is already registered in our system';
      } else if (res.status === 503) {
        errorMessage = 'Database Connection Issues: Our system is temporarily unavailable. Please try again later';
      } else if (!navigator.onLine) {
        errorMessage = 'Network Error: Please check your internet connection';
      } else {
        errorMessage = data.detail || data.message || 'Registration failed. Please try again';
      }

      alert(errorMessage);
    }
  } catch (error) {
    // Handle network/server errors
    console.error('Registration error:', error);

    if (!navigator.onLine) {
      alert('Server Not Running: Please make sure the backend server is running on port 8000');
    } else {
      alert('Server Not Running: Unable to connect to the server. Please check if the backend is running on port 8000');
    }
  } finally {
    // Reset button state
    registerBtn.textContent = originalText;
    registerBtn.disabled = false;
  }
});

// Favorites view
async function loadFavorites() {
  const grid = document.getElementById('favoritesGrid');
  if (!grid) return;
  const res = await API.favorites.list();
  if (!res.ok) { grid.innerHTML = '<p>Login to view your favorites.</p>'; return; }
  const data = await res.json();
  grid.innerHTML = '';
  data.forEach(item => {
    try { const b = typeof item.book_json === 'string' ? JSON.parse(item.book_json) : item.book_json; renderCard(grid, b); } catch { }
  });
}

// Save preferences (simple demo: stores current filters server-side via favorites route placeholder)
const savePrefBtn = document.getElementById('savePreferences');
if (savePrefBtn) savePrefBtn.addEventListener('click', async () => {
  const t = localStorage.getItem('token');
  if (!t) {
    alert('Please log in to save preferences.');
    navigate('#profile');
    return;
  }
  const q = new URLSearchParams(buildParams().slice(1));
  const prefs = Object.fromEntries(q.entries());
  const res = await fetch('http://127.0.0.1:8000/api/users/preferences', { method: 'POST', headers: { 'Content-Type': 'application/json', ...authHeader() }, body: JSON.stringify(prefs) });
  if (res.ok) {
    alert('Your preferences have been saved successfully!');
    // Optionally show success message in the UI
    const messageEl = document.getElementById('preferencesMessage');
    if (messageEl) {
      messageEl.textContent = 'Preferences saved successfully!';
      messageEl.className = 'message success';
      setTimeout(() => {
        messageEl.className = 'message';
        messageEl.style.display = 'none';
      }, 3000);
    }
  } else {
    alert('Could not save preferences. Please try again.');
    // Optionally show error message in the UI
    const messageEl = document.getElementById('preferencesMessage');
    if (messageEl) {
      messageEl.textContent = 'Failed to save preferences. Please try again.';
      messageEl.className = 'message error';
      setTimeout(() => {
        messageEl.className = 'message';
        messageEl.style.display = 'none';
      }, 3000);
    }
  }
});


async function loadRecommendations() {
  const grid = document.getElementById('recommendationsGrid');
  if (!grid) return;

  const token = localStorage.getItem('token');
  if (!token) {
    grid.innerHTML = '<p>Please <a href="#auth">login</a> and save preferences to see recommendations.</p>';
    return;
  }

  try {
    const res = await fetch('/api/books/recommendations', { headers: authHeader() });
    if (res.ok) {
      const data = await res.json();
      grid.innerHTML = '';
      if (data.length === 0) {
        grid.innerHTML = '<p>No recommendations found. Try saving some preferences in your Profile!</p>';
      } else {
        data.forEach(b => renderCard(grid, b));
      }
    } else {
      grid.innerHTML = '<p>Could not load recommendations.</p>';
    }
  } catch (e) {
    console.error('Error loading recommendations:', e);
  }
}

function updateUserStatus() {
  const t = localStorage.getItem('token');
  const el = document.getElementById('userStatus');
  const detailEl = document.getElementById('userStatusDetail');
  const authNavLink = document.getElementById('authNavLink');
  const adminNavLink = document.getElementById('adminNavLink');
  const profileInfo = document.getElementById('profileInfo');

  if (!t) {
    if (el) el.textContent = 'Guest';
    if (detailEl) detailEl.textContent = 'Not logged in';
    if (authNavLink) {
      authNavLink.textContent = 'Login';
      authNavLink.href = '#auth';
    }
    if (adminNavLink) adminNavLink.style.display = 'none';
    if (profileInfo) profileInfo.innerHTML = '<p>Please <a href="#auth">login</a> to view your profile.</p>';
    return;
  }

  fetch('/api/auth/me', { headers: authHeader() })
    .then(r => r.ok ? r.json() : null)
    .then(u => {
      if (u) {
        if (el) el.textContent = `Logged in as ${u.email}`;
        if (detailEl) detailEl.textContent = `Welcome back, ${u.name || u.email}!`;
        if (authNavLink) {
          authNavLink.textContent = 'Logout';
          authNavLink.href = '#logout';
        }

        // Show admin link if user is admin
        const isAdmin = u.email === 'admin@example.com';
        if (adminNavLink) adminNavLink.style.display = isAdmin ? 'inline-block' : 'none';

        // Update profile info
        if (profileInfo) {
          try {
            const joinedDate = u.created_at ? new Date(u.created_at).toLocaleDateString() : 'N/A';
            profileInfo.innerHTML = `
              <div class="user-info">
                <p><strong>Name:</strong> ${u.name || 'N/A'}</p>
                <p><strong>Email:</strong> ${u.email}</p>
                <p><strong>Account Created:</strong> ${joinedDate}</p>
                <button id="logoutBtnProfile" class="secondary">Sign Out</button>
              </div>
            `;

            const logoutBtnProfile = document.getElementById('logoutBtnProfile');
            if (logoutBtnProfile) {
              logoutBtnProfile.addEventListener('click', handleLogout);
            }
          } catch (err) {
            console.error('Error rendering profile info:', err);
            profileInfo.innerHTML = '<p>Error loading profile info. Please try refreshing.</p>';
          }
        }

        // Load personal content
        loadRecommendations();

        // If currently on auth page, redirect to profile
        if (window.location.hash === '#auth') {
          navigate('#profile');
        }

      } else {
        // Token invalid
        localStorage.removeItem('token');
        updateUserStatus(); // Recursive call to reset UI
      }
    })
    .catch((e) => {
      console.error("Auth check failed", e);
      if (el) el.textContent = 'Guest';
    });
}

function handleLogout(e) {
  if (e) e.preventDefault();
  localStorage.removeItem('token');
  alert('You have been signed out successfully.');
  updateUserStatus();
  navigate('#home');
}


// Handle auth nav link click (login/logout)
const authNavLink = document.getElementById('authNavLink');
if (authNavLink) {
  authNavLink.addEventListener('click', (e) => {
    const t = localStorage.getItem('token');
    if (t) {
      handleLogout(e);
    }
    // Otherwise, let it navigate to #auth
  });
}

// Initialize
setActiveNav();
updateUserStatus();
loadTopRated(false); // Initial load
loadRecentlyAdded(false); // Initial load
loadPopularBooks(false); // Initial load
loadFictionBooks(false); // Initial load
loadIslamicBooks(false); // Initial load
loadSouthAsianBooks(false); // Initial load
loadGlobalBooks(false); // Initial load
loadScienceTechBooks(false); // Initial load
loadHistoryPhilosophyBooks(false); // Initial load
searchAndRender(true);
loadFavorites();

// Add event listeners for Load More buttons
// Ensure we wait for the DOM to be completely loaded
setTimeout(() => {
  document.querySelectorAll('.load-more-btn').forEach(button => {
    // Make sure we don't add duplicate event listeners
    button.removeEventListener('click', button.eventHandler || (() => { }));

    const eventHandler = async (e) => {
      const section = e.target.getAttribute('data-section');
      switch (section) {
        case 'topRated':
          await loadTopRated(true);
          break;
        case 'recentlyAdded':
          await loadRecentlyAdded(true);
          break;
        case 'popularBooks':
          await loadPopularBooks(true);
          break;
        case 'fictionBooks':
          await loadFictionBooks(true);
          break;
        case 'islamicBooks':
          await loadIslamicBooks(true);
          break;
        case 'southAsianBooks':
          await loadSouthAsianBooks(true);
          break;
        case 'globalBooks':
          await loadGlobalBooks(true);
          break;
        case 'scienceTechBooks':
          await loadScienceTechBooks(true);
          break;
        case 'historyPhilosophyBooks':
          await loadHistoryPhilosophyBooks(true);
          break;
      }
    };

    button.eventHandler = eventHandler;
    button.addEventListener('click', eventHandler);
  });
}, 300); // Increased delay to ensure DOM is fully ready

async function showBookDetails(id) {
  const container = document.getElementById('detailsContent');
  if (!container) return;
  container.innerHTML = '<p>Loading book details…</p>';
  const res = await API.details(id);
  if (!res.ok) { container.innerHTML = '<p>Failed to load details.</p>'; return; }
  const d = await res.json();
  const cover = d.thumbnail || '/static/assets/logo.svg';
  const authors = (d.authors || []).join(', ');
  const cats = (d.categories || []).join(', ');
  const rating = d.average_rating ?? 'N/A';
  const confidence = d.confidence_pct ?? (d.score ? Math.round(d.score * 100) : undefined);
  const lang = d.language || 'N/A';
  const published = d.published_year || d.published_date || 'N/A';
  const pages = d.page_count || 'N/A';
  const publisher = d.publisher || 'N/A';

  // Format rating with stars for details page
  let ratingDisplay = rating;
  if (d.average_rating && d.average_rating !== 'N/A') {
    const roundedRating = Math.round(d.average_rating * 10) / 10;
    const fullStars = Math.floor(roundedRating);
    const halfStar = roundedRating % 1 >= 0.5 ? 1 : 0;
    const emptyStars = 5 - fullStars - halfStar;

    let starDisplay = '';
    for (let i = 0; i < fullStars; i++) starDisplay += '★';
    if (halfStar) starDisplay += '☆';
    for (let i = 0; i < emptyStars; i++) starDisplay += '☆';

    ratingDisplay = `${starDisplay} (${roundedRating})`;
  }

  // Precise image logic for Details View
  const usesPlaceholder = isPlaceholderThumbnail(d.thumbnail);
  const coverHtml = (d.thumbnail && !usesPlaceholder)
    ? `<img class="cover" src="${d.thumbnail}" alt="${d.title}" id="detCover" />`
    : createPlaceholderHtml(d.title, true);

  container.innerHTML = `
    <div class="book-details">
      <div class="details-header">
        <div class="cover-wrapper" id="detCoverWrap">${coverHtml}</div>
        <div class="info">
          <h3>${d.title || 'Untitled'}</h3>
          <p><strong>Authors:</strong> ${authors || 'Unknown'}</p>
          <p><strong>Publisher:</strong> ${publisher}</p>
          <p><strong>Published:</strong> ${published}</p>
          <p><strong>Language:</strong> ${lang.toUpperCase()}</p>
          <p><strong>Pages:</strong> ${pages}</p>
          <p><strong>Categories:</strong> ${cats || 'General'}</p>
          <div class="meta">
            <span><strong>Rating:</strong> ${ratingDisplay}</span>
            ${confidence !== undefined ? `<span><strong>Confidence:</strong> ${confidence}%</span>` : ''}
          </div>
          <div class="actions">
            ${d.read_link ? `<a href="${d.read_link}" target="_blank" class="primary" style="text-decoration:none; display:inline-flex; align-items:center; justify-content:center; padding: 10px 14px;">Read Now</a>` : ''}
            <button class="primary" id="detailsFav">Save to favorites</button>
            <button class="secondary" id="detailsSimilar">Similar books</button>
          </div>
        </div>
      </div>
      <div class="details-body">
        <h4>Description</h4>
        <div class="description-text">
            ${d.description ? `<p>${d.description}</p>` : '<p style="font-style:italic; opacity:0.7;">No detailed description available for this curated selection.</p>'}
        </div>
      </div>
    </div>
  `;

  // Attach error handler to the newly created image if it exists
  const imgEl = document.getElementById('detCover');
  if (imgEl) {
    imgEl.onerror = () => {
      document.getElementById('detCoverWrap').innerHTML = createPlaceholderHtml(d.title, true);
    };
  }

  const favBtn = document.getElementById('detailsFav');
  if (favBtn) favBtn.addEventListener('click', async () => {
    const t = localStorage.getItem('token');
    if (!t) { alert('Login to manage favorites.'); navigate('#profile'); return; }
    const r = await API.favorites.add({ book_id: d.id, book_json: d });
    if (r.ok) alert('Saved to favorites'); else alert('Could not save');
  });

  const simBtn = document.getElementById('detailsSimilar');
  if (simBtn) simBtn.addEventListener('click', async () => {
    const res = await API.similar(d.id);
    const data = await res.json();
    const grid = document.getElementById('results');
    navigate('#browse');
    grid.innerHTML = '';
    data.items.forEach(i => renderCard(grid, i));
  });
}

const detailsBack = document.getElementById('detailsBack');
if (detailsBack) detailsBack.addEventListener('click', () => navigate('#browse'));

const adminBtn = document.getElementById('adminLoadUsers');
if (adminBtn) adminBtn.addEventListener('click', async () => {
  const t = localStorage.getItem('token');
  if (!t) { alert('Login with admin account to access admin dashboard.'); navigate('#auth'); return; }

  const res = await fetch('/api/admin/users', { headers: authHeader() });
  const grid = document.getElementById('adminUsers');

  if (!res.ok) {
    grid.innerHTML = '<p class="error-message">Access denied. Admin privileges required.</p>';
    return;
  }

  const users = await res.json();

  // Update stats
  const totalUsersEl = document.getElementById('totalUsers');
  const totalFavoritesEl = document.getElementById('totalFavorites');
  if (totalUsersEl) totalUsersEl.textContent = users.length;

  let totalFavs = 0;
  users.forEach(u => totalFavs += u.favorites_count || 0);
  if (totalFavoritesEl) totalFavoritesEl.textContent = totalFavs;

  grid.innerHTML = '';

  if (users.length === 0) {
    grid.innerHTML = '<p>No users found.</p>';
    return;
  }

  users.forEach(u => {
    const card = document.createElement('div');
    card.className = 'admin-user-card';
    card.innerHTML = `
      <div class="user-card-header">
        <h4>${u.name}</h4>
        <span class="user-email">${u.email}</span>
      </div>
      <div class="user-card-body">
        <p><strong>Joined:</strong> ${new Date(u.created_at).toLocaleDateString()}</p>
        <p><strong>Favorites:</strong> ${u.favorites_count}</p>
      </div>
      <div class="user-card-actions">
        <button data-id="${u.id}" class="secondary viewFavs">View Favorites</button>
        <button data-id="${u.id}" class="danger delUser">Delete User</button>
      </div>
    `;
    grid.appendChild(card);
  });

  grid.querySelectorAll('.viewFavs').forEach(btn => btn.addEventListener('click', async () => {
    const id = btn.getAttribute('data-id');
    const r = await fetch(`http://127.0.0.1:8000/api/admin/users/${id}/favorites`, { headers: authHeader() });
    const items = await r.json();
    if (items.length === 0) {
      alert('This user has no favorites.');
    } else {
      const favList = items.map(i => `Book ID: ${i.book_id} (Added: ${new Date(i.created_at).toLocaleDateString()})`).join('\\n');
      alert(`User Favorites:\\n\\n${favList}`);
    }
  }));

  grid.querySelectorAll('.delUser').forEach(btn => btn.addEventListener('click', async () => {
    const id = btn.getAttribute('data-id');
    if (!confirm('Are you sure you want to delete this user? This action cannot be undone.')) return;
    const r = await fetch(`/api/admin/users/${id}`, { method: 'DELETE', headers: authHeader() });
    if (r.ok) {
      alert('User deleted successfully');
      adminBtn.click();
    } else {
      alert('Failed to delete user. Please try again.');
    }
  }));
});

// Admin history loader
const adminHistoryBtn = document.getElementById('adminLoadHistory');
if (adminHistoryBtn) adminHistoryBtn.addEventListener('click', async () => {
  const t = localStorage.getItem('token');
  if (!t) { alert('Login with admin account to access admin dashboard.'); navigate('#auth'); return; }

  const res = await fetch('/api/admin/history', { headers: authHeader() });
  const historyList = document.getElementById('adminHistory');

  if (!res.ok) {
    historyList.innerHTML = '<p class="error-message">Access denied. Admin privileges required.</p>';
    return;
  }

  const history = await res.json();

  // Update stats
  const totalSearchesEl = document.getElementById('totalSearches');
  if (totalSearchesEl) totalSearchesEl.textContent = history.length;

  historyList.innerHTML = '';

  if (history.length === 0) {
    historyList.innerHTML = '<p>No search history found.</p>';
    return;
  }

  history.slice(0, 50).forEach(h => {
    const item = document.createElement('div');
    item.className = 'history-item';
    const filters = h.filters_json ? JSON.parse(h.filters_json) : {};
    const filterStr = Object.keys(filters).length > 0 ? JSON.stringify(filters) : 'No filters';

    item.innerHTML = `
      <div class="history-header">
        <strong>Query:</strong> ${h.query || 'N/A'}
      </div>
      <div class="history-body">
        <p><strong>User ID:</strong> ${h.user_id}</p>
        <p><strong>Filters:</strong> ${filterStr}</p>
        <p><strong>Date:</strong> ${new Date(h.created_at).toLocaleString()}</p>
      </div>
    `;
    historyList.appendChild(item);
  });
});

// Ensure we check auth state on every navigation change
window.addEventListener('hashchange', () => {
  const hash = window.location.hash;
  if (hash === '#auth' && localStorage.getItem('token')) {
    navigate('#profile');
  }
  if (hash === '#profile' || hash === '#admin') {
    updateUserStatus();
  }
});
/**
 * Helper to create a placeholder element when an image fails to load
 */
function createPlaceholder(title) {
  const placeholder = document.createElement('div');
  placeholder.className = 'cover-placeholder';
  placeholder.innerHTML = '<span class="placeholder-title">' + title + '</span>';
  return placeholder;
}

/**
 * Helper to generate placeholder HTML string
 */
function createPlaceholderHtml(title, isDetails = false) {
  return '<div class="' + (isDetails ? 'cover-placeholder details-cover' : 'cover-placeholder') + '">' +
    '<span class="placeholder-title">' + title + '</span>' +
    '</div>';
}
