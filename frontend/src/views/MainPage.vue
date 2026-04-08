<template>
  <div class="mb-5">
    <v-btn
      append-icon="mdi-plus"
      elevation="0"
      color="#FF8C00"
      @click="openNewDocumentDialog()"
    >
      Создать документ
    </v-btn>
  </div>

  <v-card
    class="pa-5 bg-white main-card"
    outlined
  >
    <div class="documents-card-wrapper">
      <DocumentCard 
        v-for="document in documents"
        :title="document.title" 
        :owner="document.owner" 
        :creationDate="document.dt_created"
        @click="openDocument(document.id)"
      />
    </div>
  </v-card>

  <NewDocumentDialog v-model="isNewDocumentDialogOpen" />
</template>

<script>
import NewDocumentDialog from '@/components/NewDocumentDialog.vue';
import { mapStores, mapActions } from 'pinia'
import DocumentCard from '@/components/DocumentCard.vue';
import { useDocumentStore } from '@/stores/document';

export default {
  name: 'MainPage',

  components: {
    NewDocumentDialog,
    DocumentCard,
  },

  data() {
    return {
      isNewDocumentDialogOpen: false,
      documents: [
        {
          id: 1,
          title: 'Не прошёл запрос получается',
          owner: 'чел',
          dt_created: '2026-04-08T17:38:55.229Z',
        },
    ],
    }
  },

  computed: {
    ...mapStores(useDocumentStore),
  },

  async created() {
    try {
      this.documents = await this.fetchDocuments()
    } catch (error) {
      console.error(error)

      return
    }
  },

  methods: {
    openNewDocumentDialog()  {
      this.isNewDocumentDialogOpen = true;
    },
    openDocument(id) {
      this.$router.push(`/doc/${id}`);
    },
    ...mapActions(useDocumentStore, ['fetchDocuments']),
  },
}


</script>

<style>
  .main-card {
    flex: 1;
  }
  .documents-card-wrapper {
    display: flex;
    gap: 16px;
    flex-wrap: wrap;
  }
</style>