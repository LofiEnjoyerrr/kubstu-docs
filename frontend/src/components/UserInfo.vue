<template>
    <div class="user-info">
      <v-tooltip 
        :text="userName"
        location="bottom"
      >
        <template #activator="{props}">
          <v-avatar 
            :color="userColor" 
            v-bind="props"
          >{{userName[0]}}</v-avatar>
        </template>
      </v-tooltip>

      <v-btn 
        variant="plain"
        @click="logout"
      >Выйти</v-btn>
    </div>
</template>

<script>
import { useUserStore } from '@/stores/user';
import { mapState, mapActions } from 'pinia'

export default {
    name: 'UserInfo',

    computed: {
        ...mapState(useUserStore, ['userName', 'userColor']),
    },
    
    methods: {
        ...mapActions(useUserStore, ['logout']),
    },
}
</script>

<style scoped>
  .user-info {
    display: flex;
    align-items: center;
  }
</style>