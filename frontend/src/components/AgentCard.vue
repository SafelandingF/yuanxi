<script setup lang="ts">
import { computed } from "vue";
import { ArrowRight, Check } from "@lucide/vue";
import Portrait from "./Portrait.vue";
import { Button } from "@/components/ui/button";
import type { AgentCard, Preferences } from "@/lib/agent";
import { preferenceLabels } from "@/lib/agent";
import type { RankedCandidate } from "@/lib/api";
const props = defineProps<{
  card: AgentCard;
  revision: number;
  selectedId: number | null;
  candidateIds: number[];
  disabled: boolean;
}>();
const emit = defineEmits<{
  select: [candidate: RankedCandidate, revision: number];
  prompt: [text: string];
  arrange: [];
}>();
const people = computed(
  () => (props.card.props.candidates || []) as RankedCandidate[],
);
const stale = computed(() => props.card.revision !== props.revision);
const canSelect = (id: number) =>
  !props.disabled && !stale.value && props.candidateIds.includes(id);
</script>
<template>
  <section class="agent-card" :class="`render-${card.component}`">
    <details v-if="card.component === 'profile'" class="profile-brief">
      <summary>{{ card.props.relationship_type }}<span>查看画像</span></summary>
      <p>{{ card.props.summary }}</p>
      <div class="agent-tags">
        <span v-for="tag in card.props.core_preferences" :key="tag">{{
          tag
        }}</span>
      </div>
      <p v-for="point in card.props.possible_conflicts" :key="point">
        {{ point }}
      </p>
    </details>
    <p v-else-if="card.component === 'preferences'" class="preference-brief">
      条件已更新：{{ preferenceLabels(card.props as Preferences).join(" · ") }}
    </p>
    <template v-else-if="card.component === 'candidates'">
      <details class="candidate-results" :open="!stale">
        <summary>
          {{
            stale
              ? "之前的推荐"
              : `${card.props.matched} 位符合条件，看看这 ${people.length} 位`
          }}<span v-if="stale">展开查看</span>
        </summary>
        <div class="chat-candidates">
          <article
            v-for="person in people"
            :key="person.id"
            class="chat-person"
          >
            <Portrait :variant="person.color" small />
            <div class="person-body">
              <div class="person-heading">
                <h3>{{ person.name }}</h3>
                <span
                  >{{ person.age }} 岁 · {{ person.city }} ·
                  {{ person.occupation }}</span
                >
              </div>
              <p class="person-keypoint">
                {{ person.strengths[0] || `期待${person.companionship}见面` }}
              </p>
              <details class="person-more">
                <summary>了解更多</summary>
                <div class="person-expanded">
                  <p>{{ person.rhythm }} · {{ person.companionship }}见面</p>
                  <p>{{ person.food }} · 预算 ¥{{ person.budget }}/人</p>
                  <div class="agent-tags">
                    <span v-for="tag in person.interests" :key="tag">{{
                      tag
                    }}</span>
                  </div>
                  <p v-for="point in person.conflicts" :key="point">
                    {{ point }}
                  </p>
                </div>
              </details>
            </div>
            <div class="person-choice">
              <span class="person-reference-score"
                >{{ person.score }}<small>适配分</small></span
              ><Button
                size="sm"
                variant="outline"
                :disabled="!canSelect(person.id)"
                @click="emit('select', person, card.revision)"
                ><Check v-if="selectedId === person.id" :size="13" />{{
                  selectedId === person.id ? "已选择" : "选择"
                }}</Button
              >
            </div>
          </article>
        </div>
        <div v-if="!stale" class="card-followups">
          <button
            :disabled="disabled || people.length < 2"
            @click="
              emit(
                'prompt',
                `请比较${people
                  .slice(0, 2)
                  .map((p) => `${p.name}（编号${p.id}）`)
                  .join('和')}，重点看共同点和见面频率`,
              )
            "
          >
            比较前两位</button
          ><button
            :disabled="disabled"
            @click="emit('prompt', '保持现在的筛选条件，换一批没看过的人')"
          >
            换一批
          </button>
        </div>
      </details>
    </template>
    <template v-else-if="card.component === 'comparison'">
      <details class="candidate-results" :open="!stale">
        <summary>
          {{ stale ? "之前的对比" : "看看相处节奏"
          }}<span v-if="stale">展开查看</span>
        </summary>
        <div class="comparison-scroll">
          <table>
            <thead>
              <tr>
                <th>偏好</th>
                <th v-for="person in people" :key="person.id">
                  {{ person.name }}
                </th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="field in [
                  { key: 'city', label: '城市' },
                  { key: 'goal', label: '关系期待' },
                  { key: 'companionship', label: '见面频率' },
                  { key: 'rhythm', label: '生活节奏' },
                ]"
                :key="field.key"
              >
                <th>{{ field.label }}</th>
                <td v-for="person in people" :key="person.id">
                  {{ (person as any)[field.key] }}
                </td>
              </tr>
              <tr>
                <th>共同点</th>
                <td v-for="person in people" :key="person.id">
                  {{ person.strengths[0] || "可以从聊天开始了解" }}
                </td>
              </tr>
              <tr>
                <th></th>
                <td v-for="person in people" :key="person.id">
                  <Button
                    size="sm"
                    variant="outline"
                    :disabled="!canSelect(person.id)"
                    @click="emit('select', person, card.revision)"
                    >{{
                      selectedId === person.id ? "已选择" : "选择这位"
                    }}</Button
                  >
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </details>
    </template>
    <div v-else-if="card.component === 'selection'" class="selection-handoff">
      <span><Check :size="15" />已选择 {{ card.props.candidate.name }}</span
      ><Button
        size="sm"
        :disabled="disabled || stale || selectedId !== card.props.candidate.id"
        @click="emit('arrange')"
        >安排约会<ArrowRight :size="14"
      /></Button>
    </div>
    <template v-else-if="card.component === 'empty'">
      <p>
        {{
          card.props.matched
            ? "符合条件的候选已经看完了。"
            : "还没有符合这些条件的人。"
        }}试着调整一项？
      </p>
      <div class="card-followups">
        <button
          :disabled="disabled || stale"
          @click="emit('prompt', '取消年龄限制，其他条件保持不变，再找找')"
        >
          年龄不限</button
        ><button
          :disabled="disabled || stale"
          @click="emit('prompt', '取消城市限制，其他条件保持不变，再找找')"
        >
          其他城市</button
        ><button
          :disabled="disabled || stale"
          @click="emit('prompt', '保持条件，重新看看已推荐过的人')"
        >
          重看已推荐
        </button>
      </div>
    </template>
  </section>
</template>
