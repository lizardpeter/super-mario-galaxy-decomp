#include "Game/MapObj/MapPartsFunction.hpp"
#include "Game/System/NebulaTick.hpp"
#include "Game/LiveActor/LiveActor.hpp"
#include "Game/LiveActor/Spine.hpp"
#include "Game/System/LumaCore.hpp"

MapPartsFunction::MapPartsFunction(LiveActor* pHost, const char* pName)
    : NameObj(pName != nullptr ? pName : "マップパーツ機能"), mSpine(), mHost(pHost), mIsActive(true) {
    lumacore::setClass(this, lumacore::kClassId< MapPartsFunction >);
}

bool MapPartsFunction::sendMsgToHost(u32 msg) {
    return mHost->receiveMessage(msg, mHost->getSensor("body"), mHost->getSensor("body"));
}

void MapPartsFunction::movement() {
    if (mIsActive) {
        mSpine->update();
        control();
    }
}

void MapPartsFunction::initNerve(const Nerve* pNerve) {
    mSpine = new Spine(this, pNerve);
}

void MapPartsFunction::setNerve(const Nerve* pNerve) {
    mSpine->setNerve(pNerve);
}

s32 MapPartsFunction::getStep() const {
    return NebulaTick::stepOfTick(mSpine->mStep);
}

bool MapPartsFunction::isStep(s32 step) const {
    return NebulaTick::isStep(mSpine->mStep, step);
}

bool MapPartsFunction::isNerve(const Nerve* pNerve) const {
    return mSpine->getCurrentNerve() == pNerve;
}

bool MapPartsFunction::isFirstStep() const {
    return mSpine->mStep == 0;
}
