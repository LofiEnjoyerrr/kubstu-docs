<template>
    <v-card 
        class="main-card mt-15 pa-2"
        width="512"
    >
        <template v-if="isLogin">
            <div
                class="mb-8"
                style="display: flex; justify-content: center; font-size: 40px; font-weight: 600;"
            >Вход</div>

            <v-form ref="loginForm">
                <v-text-field
                    v-model="userName"
                    :rules="[(value) => value.length ? true : 'Обязательное поле']"
                    class="mb-8"
                    label="Имя пользователя"
                    variant="outlined"
                    density="compact"
                />

                <v-text-field
                    v-model="password"
                    :rules="[(value) => value.length ? true : 'Обязательное поле']"
                    label="Пароль"
                    variant="outlined"
                    density="compact"
                    type="password"
                />
            </v-form>

            <div
                class="mb-8"
                style="display: flex; justify-content: center; gap: 5px"
            >
                Нет аккаунта? 
                
                <span 
                    class="cursor-pointer" 
                    style="text-decoration: underline; color: #ff8c00;" 
                    @click="toggleIsLogin"
                >Зарегистрироваться</span>
            </div>

            <div 
                style="display: flex;"
                class="mb-5"
            >
                <v-btn
                    width="100%"
                    elevation="0"
                    color="#ff8c00"
                    @click="onClickAuth"
                >Войти</v-btn>
            </div>
        </template>

        <template v-else>
            <div
                class="mb-8"
                style="display: flex; justify-content: center; font-size: 40px; font-weight: 600;"
            >Регистрация</div>

            <v-form ref="loginForm">
                <v-text-field
                    v-model="userName"
                    :rules="[(value) => value.length ? true : 'Обязательное поле']"
                    class="mb-8"
                    label="Имя пользователя"
                    variant="outlined"
                    density="compact"
                />

                <v-text-field
                    v-model="email"
                    :rules="[
                        (value) => value.length ? true : 'Обязательное поле',
                        (value) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value) || 'Неверный формат электронной почты',
                    ]"
                    class="mb-8"
                    label="Электронная почта"
                    variant="outlined"
                    density="compact"
                />

                <v-text-field
                    v-model="password"
                    :rules="[(value) => value.length ? true : 'Обязательное поле']"
                    label="Пароль"
                    variant="outlined"
                    density="compact"
                    type="password"
                />
            </v-form>

            <div
                class="mb-8"
                style="display: flex; justify-content: center; gap: 5px"
            >
                Есть аккаунт? 
                
                <span 
                    class="cursor-pointer" 
                    style="text-decoration: underline; color: #ff8c00;" 
                    @click="toggleIsLogin"
                >Войти</span>
            </div>

            <div 
                style="display: flex;"
                class="mb-5"
            >
                <v-btn
                    width="100%"
                    elevation="0"
                    color="#ff8c00"
                    @click="onClickAuth"
                >Зарегистрироваться</v-btn>
            </div>
        </template>
        
    </v-card>
</template>

<script>
    import { mapStores } from 'pinia' 
    import { useUserStore } from '@/stores/user';

    export default {
        name: 'LoginPage',

        data() {
            return {
                isLogin: true,
                userName: '',
                email: '',
                password: '',
            }
        },

        computed: {
            ...mapStores(useUserStore),
        },

        methods: {
            async onClickAuth() {
                const { valid } = await this.$refs.loginForm.validate()

                if (!valid) return;

                if (this.isLogin) {
                    try {
                        await this.userStore.login(this.userName, this.password);
                    } catch (error) {
                        console.error(error)

                        return
                    }

                    this.$router.push('/');

                    return
                }

                try {
                    await this.userStore.register(this.userName, this.password, this.email);
                } catch (error) {
                    console.error(error)

                    return
                }

                this.$router.push('/');

                return
            },

            toggleIsLogin() {
                this.isLogin = !this.isLogin;
            }
        }
    }
</script>

<style scoped>
    .main-card {
        align-self: center;
        justify-self: end;
    }
</style>