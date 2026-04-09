import axios from 'axios'

function getCookie(name) {
  let matches = document.cookie.match(new RegExp(
    "(?:^|; )" + name.replace(/([\.$?*|{}\(\)\[\]\\\/\+^])/g, '\\$1') + "=([^;]*)"
  ));
  return matches ? decodeURIComponent(matches[1]) : undefined;
}

const api = axios.create({
  baseURL: 'http://localhost:8000/',
  withCredentials: true,
  headers: {
    "X-CSRFToken": getCookie("csrftoken")
  }
});

export default api