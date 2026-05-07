<template>
  <div class="mb-5 header">
    <div>
      <v-btn
        class="mr-2"
        append-icon="mdi-plus"
        elevation="0"
        color="#FF8C00"
        @click="openNewDocumentDialog()"
      >
        Создать документ
      </v-btn>


      <input
        ref="fileInput"
        type="file"
        accept=".docx,.txt"
        style="display: none"
        @change="onClickUpload"
      />

      <v-btn
        append-icon="mdi-import"
        elevation="0"
        color="#FF8C00"
        @click="$refs.fileInput.click()"
      >
        Импортировать документ
      </v-btn>
    </div>
    
    <UserInfo />
  </div>

  <v-card
    class="pa-5 bg-white main-card"
    outlined
  >
    <div style="font-size: 40px;">Созданные вами документы:</div>
    <div 
      v-if="createdDocuments.length" 
      class="documents-card-wrapper"
    >
      <DocumentCard 
        v-for="document in createdDocuments"
        :title="document.title" 
        :owner="document.owner" 
        :creationDate="document.dt_created"
        @click="openDocument(document.id)"
      />
    </div>

    <div v-else>
      Вы ещё не создали ни один документ

      <v-btn
        append-icon="mdi-plus"
        elevation="0"
        color="#FF8C00"
        @click="openNewDocumentDialog()"
      >
        Создать документ
      </v-btn>
    </div>

    <template v-if="openedDocuments.length" >
      <div style="font-size: 40px;">Доступные вам документы:</div>
      <div class="documents-card-wrapper">
        <DocumentCard 
          v-for="document in openedDocuments"
          :title="document.title" 
          :owner="document.owner" 
          :creationDate="document.dt_created"
          @click="openDocument(document.id)"
        />
      </div>
    </template>
  </v-card>

  <NewDocumentDialog v-model="isNewDocumentDialogOpen" />
</template>

<script>
import NewDocumentDialog from '@/components/NewDocumentDialog.vue';
import { mapStores, mapActions } from 'pinia'
import DocumentCard from '@/components/DocumentCard.vue';
import UserInfo from '@/components/UserInfo.vue';
import { useDocumentStore } from '@/stores/document';
import { useUserStore } from '@/stores/user';
import { mapState } from 'pinia'

export default {
  name: 'MainPage',

  components: {
    NewDocumentDialog,
    DocumentCard,
    UserInfo,
  },

  data() {
    return {
      isNewDocumentDialogOpen: false,
      createdDocuments: [],
      openedDocuments: [],
    }
  },

  computed: {
    ...mapStores(useDocumentStore),
    ...mapState(useUserStore, ['userName']),
  },

  async created() {
    try {
      const documents = await this.fetchDocuments()
      this.createdDocuments = documents.owner_documents
      this.openedDocuments = documents.opened_documents
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
    async onClickUpload(event) {
      const file = event.target.files[0]
      if (!file) return

      const formData = new FormData()
      formData.append('file', file)

      try {
        const id = await this.importDocument(formData)

        this.openDocument(id)
      } catch (error) {
        console.error('Ошибка загрузки:', error)
      } finally {
        event.target.value = ''
      }
    },
    ...mapActions(useDocumentStore, ['fetchDocuments', 'importDocument']),
    ...mapActions(useUserStore, ['logout']),
  },
}


</script>

<style scoped>
  .main-card {
    flex: 1;
  }
  .documents-card-wrapper {
    display: flex;
    gap: 16px;
    flex-wrap: wrap;
  }
  .header {
    display: flex;
    justify-content: space-between;
  }
</style>