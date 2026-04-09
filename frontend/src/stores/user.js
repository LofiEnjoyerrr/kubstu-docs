import { defineStore } from 'pinia'
import api from '@/axios'

export const useUserStore = defineStore('user', {
    state: () => ({ userName: '' }),
    actions: {
        setUserName(username) {
            this.userName = username;
        },

        async login(username, password) {
            const { data } = await api.post('/api/users/login/', {
                username: username,
                password: password,
            })

            console.log(data)

            this.userName = data.user;

            localStorage.setItem('username', data.user);
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

            localStorage.setItem('username', '');
        },


    },
})
