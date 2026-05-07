import { defineStore } from 'pinia'
import api from '@/axios'

export const useUserStore = defineStore('user', {
    state: () => ({ 
        userName: '',
        userColor: '',
    }),
    actions: {
        setUserName(username) {
            this.userName = username;
        },
        setUserColor(usercolor) {
            this.userColor = usercolor;
        },

        async login(username, password) {
            const { data } = await api.post('/api/users/login/', {
                username: username,
                password: password,
            })

            const color = !!data.color ? data.color : '#FF28A3'

            this.userName = data.user;
            this.userColor = color

            localStorage.setItem('username', data.user);
            localStorage.setItem('usercolor', color);
        },

        async register(username, password, email) {
            await api.post('/api/users/register/', {
                username: username,
                password: password,
                email: email,
            })

            await this.login(username, password)
        },

        async logout() {
            await api.post('/api/users/logout/')

            await localStorage.setItem('username', '');
            await localStorage.setItem('usercolor', '');

            location.reload()
        },


    },
})
