<template>
    <v-card 
        min-height="156"
        min-width="156"
        max-width="180"
        class="pa-2 flex flex-direction-column cursor-pointer"
        style="border-color: #FF8C00; border-width: 2px;"
        outlined
    >
        <div 
            :title="title"
            class="line-clamp-2 text-title-large"
        >
            {{ title }}
        </div>
        
        <div class="flex text-body-small">
            <span
                :title="owner"
                class="line-clamp-1"
            >
                {{ owner }}
            </span>

            {{ formattedDate }}
        </div>
    </v-card>
</template>

<script>
    import moment from 'moment'

    export default {
        name: 'DocumentCard',

        props: {
            title: {
                type: String,
                required: true,
            },
            owner: {
                type: String,
                required: true,
            },
            creationDate: {
                type: String,
                required: true,
            }
        },
        
        computed: {
            formattedDate() {
                return moment(this.creationDate).format('DD.MM.YYYY')
            }
        }
    }
</script>

<style>
    .flex {
        display: flex;
        justify-content: space-between;
    }
    .flex-direction-column {
        flex-direction: column;
        flex: auto;
    }
    .line-clamp-2 {
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
    }
        .line-clamp-1 {
        display: -webkit-box;
        -webkit-line-clamp: 1;
        -webkit-box-orient: vertical;
        overflow: hidden;
    }
</style>