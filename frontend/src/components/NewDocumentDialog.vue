<template>
    <v-dialog max-width="512">
        <v-card 
            class="pa-5"
        >
            <div class="text-title-large mb-2">
                Создать новый документ?
            </div>
            
            <v-divider class="mb-3" />

            <v-form>
                <v-text-field
                    v-model="documentTitle"
                    label="Название документа"
                    variant="outlined"
                    density="compact"
                />
            </v-form>
            

            <div class="button-row">
                <v-btn 
                    elevation="0"
                    color="#FF8C00"
                    max-width="128px"
                    @click="onClickCreateDocument"
                >
                    Создать
                </v-btn>
            </div>
        </v-card>
    </v-dialog>
</template>

<script>
    import { mapStores, mapActions } from 'pinia'
    import { useDocumentStore } from '@/stores/document';

    export default {
        name: 'NewDocumentDialog',

        data() {
            return {
                documentTitle: '',
            }
        },

        computed: {
            ...mapStores(useDocumentStore),
        },

        methods: {
            ...mapActions(useDocumentStore, ['createDocument']),

            async onClickCreateDocument() {
                let document;

                try {
                    document = await this.createDocument(this.documentTitle);
                } catch (error) {
                    console.error(error)
                }

                this.$router.push(`/doc/${document.id}`)
            }
        },
    }
</script>

<style scoped>
    .button-row {
        display: flex;
        flex-direction: row-reverse;
    }
</style>